"""Update check and self-update from GitHub releases.

Checks at most every 12 hours, only in an interactive terminal, and stays silent
when offline. Disable with ODVM_NO_UPDATE_CHECK=1.
"""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__, ui
from .i18n import t

REPO = "talhacevikk36/OpenDroidVM"
CHECK_EVERY = 12 * 3600
ASK_AGAIN = 24 * 3600
EXE_NAMES = {"Windows": "odvm-windows-x64.exe", "Darwin": "odvm-macos", "Linux": "odvm-linux-x64"}


def api_url():
    return os.environ.get("ODVM_UPDATE_API", f"https://api.github.com/repos/{REPO}/releases/latest")


def parse(v):
    nums = [int(x) for x in re.findall(r"\d+", str(v).lstrip("vV").split("-")[0])][:3]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(tag, current=None):
    return parse(tag) > parse(current or __version__)


def _state_file():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "opendroidvm" / "update.json"


def _load():
    try:
        return json.loads(_state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(st):
    try:
        f = _state_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(st), encoding="utf-8")
    except OSError:
        pass


def web_base():
    return os.environ.get("ODVM_UPDATE_WEB", f"https://github.com/{REPO}").rstrip("/")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _latest_via_web(timeout=4):
    """Fallback without the API (its anonymous limit is 60/hour per IP, shared on many networks):
    /releases/latest redirects to /releases/tag/<tag>; asset URLs follow a fixed pattern."""
    req = urllib.request.Request(web_base() + "/releases/latest",
                                 headers={"User-Agent": "OpenDroidVM-updater"})
    try:
        urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout)
        return None                         # 200 without a redirect: no release
    except urllib.error.HTTPError as e:
        m = re.search(r"/releases/tag/([^/?#]+)", e.headers.get("Location", "") or "")
        if e.code not in (301, 302, 303, 307, 308) or not m:
            return None
        tag = m.group(1)
    except (urllib.error.URLError, OSError):
        return None
    base = f"{web_base()}/releases/download/{tag}/"
    names = [f"opendroidvm-{tag.lstrip('vV')}-py3-none-any.whl", *EXE_NAMES.values()]
    return {"tag": tag, "assets": {n: {"url": base + n, "size": 0, "digest": ""} for n in names}}


def latest_release(timeout=4):
    """{'tag': 'v0.8.0', 'assets': {name: {'url','size','digest'}}} or None when offline."""
    info = _latest_via_api(timeout)
    return info or _latest_via_web(timeout)


def _latest_via_api(timeout=4):
    req = urllib.request.Request(api_url(), headers={"User-Agent": "OpenDroidVM-updater",
                                                     "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not isinstance(j, dict) or not j.get("tag_name"):
        return None
    assets = {a["name"]: {"url": a.get("browser_download_url", ""), "size": a.get("size", 0),
                          "digest": a.get("digest") or ""} for a in j.get("assets", [])}
    return {"tag": j["tag_name"], "assets": assets}


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def _download(url, dest, size_hint=0, digest=""):
    req = urllib.request.Request(url, headers={"User-Agent": "OpenDroidVM-updater"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 18)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
    if size_hint and os.path.getsize(dest) != size_hint:
        raise RuntimeError("size mismatch")
    if not size_hint and os.path.getsize(dest) < 1_000_000:      # no metadata: basic sanity
        raise RuntimeError("download too small, refusing to install it")
    if digest.startswith("sha256:") and h.hexdigest() != digest[7:]:
        raise RuntimeError("checksum mismatch")


def replace_running_exe(new_file, current=None):
    """Swap the running executable for `new_file` (Windows: rename the old one aside)."""
    current = str(current or sys.executable)
    if os.name == "nt":
        old = current + ".old"
        if os.path.exists(old):
            os.remove(old)
        os.replace(current, old)          # a running .exe can be renamed, not overwritten
        os.replace(new_file, current)
    else:
        os.chmod(new_file, 0o755)
        os.replace(new_file, current)


def cleanup_old():
    """Remove the leftover *.old from a previous Windows self-update."""
    if is_frozen():
        try:
            os.remove(sys.executable + ".old")
        except OSError:
            pass


def apply_update(info):
    """Install the new version. Returns (ok, message)."""
    assets = info["assets"]
    try:
        if is_frozen():
            name = EXE_NAMES.get(platform.system())
            a = assets.get(name or "")
            if not a:
                return False, f"no asset for this system ({name})"
            tmp = sys.executable + ".new"
            _download(a["url"], tmp, a["size"], a["digest"])
            replace_running_exe(tmp)
            return True, info["tag"]
        wheel = next((a for n, a in assets.items() if n.endswith(".whl")), None)
        if not wheel:
            return False, "no wheel in the release"
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", wheel["url"]]
        if subprocess.call(cmd) != 0:      # PEP 668 systems refuse plain installs
            if subprocess.call(cmd + ["--break-system-packages"]) != 0:
                return False, "pip failed"
        return True, info["tag"]
    except (OSError, RuntimeError, urllib.error.URLError) as e:
        return False, str(e)


def offer(info, assume_yes=False):
    """Ask and update. True if the program was updated (caller should exit)."""
    print(t("upd_available", new=info["tag"], cur=__version__))
    if not (assume_yes or ui.yes(t("upd_ask"))):
        return False
    print(t("upd_downloading", name=info["tag"]))
    ok, msg = apply_update(info)
    print(t("upd_done", new=msg) if ok else t("upd_failed", e=msg))
    return ok


def check_and_offer(force=False, assume_yes=False, only_check=False):
    """Startup hook. Returns True if an update was installed."""
    if not force and (os.environ.get("ODVM_NO_UPDATE_CHECK")
                      or not (sys.stdin.isatty() and sys.stdout.isatty())):
        return False
    st, now = _load(), time.time()
    info = None
    if force or now - st.get("checked", 0) > CHECK_EVERY:
        info = latest_release()
        st["checked"] = now
        if info:
            st["latest"] = info["tag"]
        elif force:
            print(t("upd_check_fail"))
        _save(st)
    tag = (info or {}).get("tag") or st.get("latest")
    if not tag or not is_newer(tag):
        if force and tag:
            print(t("upd_latest", v=__version__))
        return False
    if only_check:
        print(t("upd_available", new=tag, cur=__version__))
        return False
    if not force and st.get("declined") == tag and now - st.get("declined_at", 0) < ASK_AGAIN:
        return False
    info = info or latest_release()
    if not info:
        return False
    if offer(info, assume_yes):
        return True
    st["declined"], st["declined_at"] = info["tag"], now
    _save(st)
    return False
