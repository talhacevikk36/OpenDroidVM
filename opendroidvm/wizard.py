"""Guided start for people who do not want to learn the commands."""
import os
import sys

from . import cli, launcher, profiles, recovery, ui
from .i18n import t


def _choose_device():
    while True:
        q = ui.ask(t("wiz_search"), "")
        items = profiles.load_all()
        if q:
            ql = q.lower()
            items = [p for p in items if ql in (p.id + p.codename + p.name + p.soc).lower()]
            if not items:
                print(t("wiz_none", q=q))
                near = profiles.suggest(q)
                if near:
                    print(t("did_you_mean", x=", ".join(near)))
                continue
        else:
            items = [profiles.find(i) for i in recovery.RECOMMENDED]
        items = items[:15]
        for n, p in enumerate(items, 1):
            print(f"{n:3}. {p.name}  [{p.soc}, {round(p.ram_mb / 1024)} GB]")
        while True:                       # keep asking for the number; 0 = search again
            n = ui.pick(t("wiz_pick"), len(items))
            if n is None:
                print(t("wiz_bad"))
            else:
                break
        if n > 0:
            return items[n - 1]


def _choose_recovery(p):
    """Returns an image path, '' for none, or None to go back."""
    local = recovery.find_local(p.id)
    opts = []
    if local:
        opts.append(("have", t("wiz_rec_have", x=local)))
    opts += [("dl", t("wiz_rec_dl")), ("file", t("wiz_rec_file")), ("skip", t("wiz_rec_skip"))]
    print(t("wiz_rec"))
    for n, (_, label) in enumerate(opts, 1):
        print(f"  {n}. {label}")
    while True:
        n = ui.pick(t("wiz_choice", d=1), len(opts), default=1)
        if n:
            break
        print(t("wiz_bad"))
    kind = opts[n - 1][0]
    if kind == "have":
        return str(local)
    if kind == "skip":
        return ""
    if kind == "file":
        path = ui.ask(t("wiz_path"), "")
        if not os.path.isfile(path):
            print(t("file_not_found", x=path))
            return None
        return path
    try:
        img = recovery.fetch_profile(p, None, None, cli.progress_bar())
        if sys.stderr.isatty():
            sys.stderr.write("\n")
        return str(img)
    except recovery.FetchError as e:
        print(t("fetch_fail", id=p.id, why=e))
        return None


def _choose_mode():
    print(t("wiz_mode"))
    print("  1. " + t("wiz_fast"))
    print("  2. " + t("wiz_acc"))
    while True:
        n = ui.pick(t("wiz_choice", d=1), 2, default=1)
        if n:
            return "fast" if n == 1 else "accurate"
        print(t("wiz_bad"))


def run():
    try:
        print(t("wiz_title"))
        print(t("alpha_note"))
        p = _choose_device()
        if not recovery.find_local(p.id) and not cli._compat_ok(p, False, interactive=True):
            return 0
        img = None
        while img is None:
            img = _choose_recovery(p)
        mode = _choose_mode()
        if not ui.yes(t("wiz_confirm", name=p.name)):
            return 0
        o = launcher.Options(mode=mode, recovery=img)
        print(t("wiz_tips", adb=o.adb_port))
        return cli.launch(p, o)
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
    finally:
        if getattr(sys, "frozen", False):       # double-clicked .exe: keep the window open
            ui.ask(t("wiz_enter"), "")
