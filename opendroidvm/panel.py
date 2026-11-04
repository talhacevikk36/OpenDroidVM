"""Small tkinter panel: Power, Volume +/-, Home, Back, Menu, Recents."""
from . import keys
from .i18n import t

LAYOUT = ["volup", "voldown", "power", "home", "back", "menu", "mute", "recents"]


def run(port=keys.DEFAULT_MONITOR_PORT, via="monitor", serial="localhost:5555"):
    try:
        import tkinter as tk
    except ImportError:
        raise RuntimeError(t("tk_missing"))
    root = tk.Tk()
    root.title(t("panel_title"))
    status = tk.StringVar(value=t("panel_ready"))
    pressed = {}

    def fire(name, hold=0):
        use = "adb" if keys.KEYS[name][0] is None else via
        try:
            keys.press(name, use, port, hold, serial)
            status.set(t("panel_sent", x=name) + (f" ({hold} ms)" if hold else ""))
        except Exception as e:  # noqa: BLE001 - shown to the user
            status.set(t("panel_err", x=e))

    def down(name):
        pressed[name] = root.after(800, lambda: (pressed.pop(name, None), fire(name, 1000)))

    def up(name):
        job = pressed.pop(name, None)
        if job:
            root.after_cancel(job)
            fire(name)

    for i, name in enumerate(LAYOUT):
        b = tk.Button(root, text=t("b_" + name), width=10, height=2)
        b.bind("<ButtonPress-1>", lambda e, n=name: down(n))
        b.bind("<ButtonRelease-1>", lambda e, n=name: up(n))
        b.grid(row=i // 2, column=i % 2, padx=4, pady=4)
    tk.Label(root, textvariable=status).grid(row=len(LAYOUT), column=0, columnspan=2)
    root.attributes("-topmost", True)
    root.mainloop()
