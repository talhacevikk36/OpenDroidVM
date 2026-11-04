"""Kucuk tkinter paneli: Guc, Ses +/-, Ana ekran, Geri, Menu, Son uygulamalar."""
from . import keys

LAYOUT = [("Ses +", "volup"), ("Ses -", "voldown"), ("Guc", "power"),
          ("Ana ekran", "home"), ("Geri", "back"), ("Menu", "menu"),
          ("Sessiz", "mute"), ("Son uyg.", "recents")]


def run(port=keys.DEFAULT_MONITOR_PORT, via="monitor", serial="localhost:5555"):
    try:
        import tkinter as tk
    except ImportError:
        raise RuntimeError("tkinter yok (Linux: sudo apt install python3-tk). "
                           "Terminalden `odvm key volup` kullanabilirsin.")
    root = tk.Tk()
    root.title("OpenDroidVM tuslar")
    status = tk.StringVar(value="Hazir. Guc: basili tutunca uzun basma.")
    pressed = {}

    def fire(name, hold=0):
        use = "adb" if keys.KEYS[name][0] is None else via
        try:
            keys.press(name, use, port, hold, serial)
            status.set(f"{name} gonderildi" + (f" ({hold} ms)" if hold else ""))
        except Exception as e:  # noqa: BLE001 - kullaniciya goster
            status.set(f"Hata: {e}")

    def down(name):
        pressed[name] = root.after(800, lambda: (pressed.pop(name, None), fire(name, 1000)))

    def up(name):
        job = pressed.pop(name, None)
        if job:
            root.after_cancel(job)
            fire(name)

    for i, (label, name) in enumerate(LAYOUT):
        b = tk.Button(root, text=label, width=10, height=2)
        b.bind("<ButtonPress-1>", lambda e, n=name: down(n))
        b.bind("<ButtonRelease-1>", lambda e, n=name: up(n))
        b.grid(row=i // 2, column=i % 2, padx=4, pady=4)
    tk.Label(root, textvariable=status).grid(row=len(LAYOUT), column=0, columnspan=2)
    root.attributes("-topmost", True)
    root.mainloop()
