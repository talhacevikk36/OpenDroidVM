"""Downloads official TWRP recovery images (from dl.twrp.me) into a local folder.

Nothing is bundled in the repository: images are fetched on request, straight
from the TWRP project, and stored as  <out>/<profile id>/<file>.img
(+ SOURCE.txt with the origin URL). TWRP is GPL-3.0 licensed software.
"""
import os
import re
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .i18n import t

UA = "Mozilla/5.0 (compatible; OpenDroidVM)"
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")
# 20 devices that normally have an official TWRP page
RECOMMENDED = ["pixel", "pixel2", "pixel3", "nexus5", "nexus5x", "nexus6p", "s4", "s5",
               "s7", "s8", "s9", "s10", "note4", "oneplus3", "oneplus5", "oneplus6",
               "oneplus7pro", "pocof1", "mia2", "redminote7"]


def host():
    return os.environ.get("ODVM_TWRP_HOST", "https://dl.twrp.me").rstrip("/")


class FetchError(Exception):
    pass


def _open(url, referer=None, timeout=40):
    h = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)


def list_files(codename):
    """Image file names on the TWRP page for `codename`, newest first (page order)."""
    if not SAFE.match(codename):
        raise FetchError(t("bad_id"))
    url = f"{host()}/{urllib.parse.quote(codename)}/"
    try:
        with _open(url) as r:
            page = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FetchError(t("fetch_404", cn=codename))
        raise FetchError(t("fetch_net", e=e))
    except (urllib.error.URLError, OSError) as e:
        raise FetchError(t("fetch_net", e=e))
    names = []
    for m in re.finditer(r'href="[^"]*?(twrp-[A-Za-z0-9._+-]+?\.(?:img\.tar|img|tar))\.html"', page):
        if m.group(1) not in names:
            names.append(m.group(1))
    if not names:
        raise FetchError(t("fetch_404", cn=codename))
    return names


def download(codename, dest_dir, version=None, progress=None):
    """Download the newest (or `version`-matching) image; returns the .img path."""
    names = list_files(codename)
    if version:
        names = [n for n in names if version in n]
        if not names:
            raise FetchError(t("fetch_version", v=version))
    name = names[0]
    url = f"{host()}/{codename}/{name}"
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    part = dest / (name + ".part")
    try:
        with _open(url, referer=url + ".html") as r, open(part, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            first = r.read(4096)
            if first[:15].lower().startswith((b"<!doctype html", b"<html")):
                raise FetchError(t("fetch_html"))
            f.write(first)
            done = len(first)
            while True:
                chunk = r.read(1 << 18)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(name, done, total)
    except (urllib.error.URLError, OSError) as e:
        part.unlink(missing_ok=True)
        raise FetchError(t("fetch_net", e=e))
    except FetchError:
        part.unlink(missing_ok=True)
        raise
    final = dest / name
    os.replace(part, final)
    if name.endswith(".tar"):             # Samsung/Odin style: recovery.img inside a tar
        final = _untar(final, dest)
    (dest / "SOURCE.txt").write_text(
        f"{url}\ndownloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "TWRP is GPL-3.0 software: https://twrp.me\n", encoding="utf-8")
    return final


def _untar(tar_path, dest):
    out = dest / (tar_path.name[:-4] if tar_path.name.endswith(".img.tar")
                  else tar_path.stem + ".img")
    with tarfile.open(tar_path) as tf:
        for m in tf.getmembers():
            if m.isfile() and m.name.endswith(".img") and ".." not in m.name:
                src = tf.extractfile(m)
                with open(out, "wb") as f:
                    f.write(src.read())
                return out
    return tar_path


def candidates(profile):
    rc = profile.recovery or {}
    first = rc.get("codename") or profile.codename or profile.id
    out = []
    for c in [first, *rc.get("alt", [])]:
        if c and c not in out:
            out.append(c)
    return out


def fetch_profile(profile, out="recovery", version=None, progress=None):
    """Try the profile's TWRP codename, then its alternates (e.g. jasmine -> jasmine_sprout)."""
    err = None
    for cn in candidates(profile):
        try:
            return download(cn, Path(out) / profile.id, version, progress)
        except FetchError as e:
            err = e
    raise err


def find_local(profile_id, out="recovery"):
    d = Path(out) / profile_id
    imgs = sorted(d.glob("*.img"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return imgs[-1] if imgs else None
