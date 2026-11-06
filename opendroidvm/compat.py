"""Measured boot compatibility of the official TWRP images (see compat_data.py)."""
from . import compat_data


def get(pid):
    """None if never measured, else {'verdict','reason','arch','soc'}."""
    return compat_data.MEASURED.get(pid)


def label(pid):
    m = get(pid)
    if not m:
        return ""
    return {"yes": "twrp:ok", "serial": "twrp:serial-only", "no": "twrp:no-boot",
            "unknown": "twrp:?"}.get(m["verdict"], "")
