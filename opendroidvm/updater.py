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

from . import __version__, display_version, ui
from .i18n import t

REPO = "talhacevikk36/OpenDroidVM"
CHECK_EVERY = 12 * 3600
ASK_AGAIN = 24 * 3600
EXE_NAMES = {"Windows": "odvm-windows-x64.exe", "Darwin": "odvm-macos", "Linux": "odvm-linux-x64"}


def api_url():
    return os.environ.get("ODVM_UPDATE_API", f"https://api.github.com/repos/{REPO}/releases?per_page=15")


_PRE = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2}
_VER = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:[-._]?(alpha|beta|rc|a|b)[-._]?(\d*))?", re.I)


def parse(v):
    """(major, minor, patch, rank, n): 0.9.1a1 < 0.9.1a2 < 0.9.1b1 < 0.9.1rc1 < 0.9.1."""
    m = _VER.match(str(v).strip())
    if not m:
        return (0, 0, 0, 3, 0)
    pre = (m.group(4) or "").lower()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            _PRE[pre] if pre else 3, int(m.group(5) or 0) if pre else 0)


def is_prerelease(v):
    return parse(v)[3] != 3


def pep440(tag):
    """v0.9.1-alpha.2 -> 0.9.1a2 (the name pip/setuptools gives the wheel)."""
    M, m, p, rank, n = parse(tag)
    return f"{M}.{m}.{p}" + ({0: "a", 1: "b", 2: "rc"}[rank] + str(n) if rank != 3 else "")


def is_newer(tag, current=None):
    return parse(tag) > parse(current or __version__)


def wants_prerelease():
    """Alpha users stay on the alpha channel; stable users only see stable releases
    unless they opt in with `odvm config set channel alpha`."""
    from . import config
    return is_prerelease(__version__) or config.get("channel") == "alpha"


def _pick(tags):
    tags = [t for t in tags if wants_prerelease() or not is_prerelease(t)]
    return max(tags, key=parse) if tags else None


def _state_file():
    from . import paths
    return paths.cache_root() / "update.json"


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


def _web_assets(tag):
    base = f"{web_base()}/releases/download/{tag}/"
    names = [f"opendroidvm-{pep440(tag)}-py3-none-any.whl", *EXE_NAMES.values()]
    return {n: {"url": base + n, "size": 0, "digest": ""} for n in names}


def _latest_via_web(timeout=4):
    """Fallback without the API (anonymous limit: 60/hour per IP, shared on many networks).
    1) the public releases.atom feed (includes pre-releases); 2) /releases/latest redirect
    (stable releases only). Asset URLs follow a fixed pattern."""
    ua = {"User-Agent": "OpenDroidVM-updater"}
    try:
        req = urllib.request.Request(web_base() + "/releases.atom", headers=ua)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            feed = r.read().decode("utf-8", "replace")
        tag = _pick(re.findall(r"/releases/tag/([^\"'<>\s?#]+)", feed))
        if tag:
            return {"tag": tag, "assets": _web_assets(tag)}
    except (urllib.error.URLError, OSError):
        pass
    req = urllib.request.Request(web_base() + "/releases/latest", headers=ua)
    try:
        urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout)
        return None                         # 200 without a redirect: no release
    except urllib.error.HTTPError as e:
        m = re.search(r"/releases/tag/([^/?#]+)", e.headers.get("Location", "") or "")
        if e.code not in (301, 302, 303, 307, 308) or not m:
            return None
        return {"tag": m.group(1), "assets": _web_assets(m.group(1))}
    except (urllib.error.URLError, OSError):
        return None


def latest_release(timeout=4):
    """{'tag': 'v0.9.1-alpha.2', 'assets': {name: {'url','size','digest'}}} or None when offline."""
    return _latest_via_api(timeout) or _latest_via_web(timeout)


def _latest_via_api(timeout=4):
    req = urllib.request.Request(api_url(), headers={"User-Agent": "OpenDroidVM-updater",
                                                     "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if isinstance(j, dict):
        j = [j]
    if not isinstance(j, list):
        return None
    rels = {x["tag_name"]: x for x in j if isinstance(x, dict) and x.get("tag_name")
            and not x.get("draft")}
    tag = _pick(list(rels))
    if not tag:
        return None
    assets = {a["name"]: {"url": a.get("browser_download_url", ""), "size": a.get("size", 0),
                          "digest": a.get("digest") or ""} for a in rels[tag].get("assets", [])}
    return {"tag": tag, "assets": assets}


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
    print(t("upd_available", new=info["tag"], cur=display_version()))
    if not (assume_yes or ui.yes(t("upd_ask"))):
        return False
    print(t("upd_downloading", name=info["tag"]))
    ok, msg = apply_update(info)
    print(t("upd_done", new=msg) if ok else t("upd_failed", e=msg))
    return ok


def check_and_offer(force=False, assume_yes=False, only_check=False):
    """Startup hook. Returns True if an update was installed."""
    from . import config
    if not force and (os.environ.get("ODVM_NO_UPDATE_CHECK") or config.get("update_check") is False
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
            print(t("upd_latest", v=display_version()))
        return False
    if only_check:
        print(t("upd_available", new=tag, cur=display_version()))
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
