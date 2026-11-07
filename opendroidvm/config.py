"""User settings in config.json (odvm config set/get/unset)."""
import json

from . import paths

SCHEMA = {                        # key: (type, allowed values or None)
    "lang": (str, ("en", "tr")),
    "mode": (str, ("accurate", "fast")),
    "qemu": (str, None),
    "adb_port": (int, None),
    "recovery_dir": (str, None),
    "update_check": (bool, None),
    "channel": (str, ("stable", "alpha")),
}


def _file():
    return paths.config_root() / "config.json"


def load():
    try:
        d = json.loads(_file().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def get(key, default=None):
    return load().get(key, default)


def parse_value(key, raw):
    if key not in SCHEMA:
        raise KeyError(key)
    typ, allowed = SCHEMA[key]
    if typ is bool:
        if str(raw).lower() in ("1", "true", "yes", "on", "e", "evet"):
            return True
        if str(raw).lower() in ("0", "false", "no", "off", "h", "hayir"):
            return False
        raise ValueError(raw)
    val = typ(raw)
    if allowed and val not in allowed:
        raise ValueError(raw)
    return val


def set_value(key, raw):
    val = parse_value(key, raw)
    d = load(); d[key] = val
    _save(d)
    return val


def unset(key):
    d = load(); d.pop(key, None); _save(d)


def _save(d):
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=2), encoding="utf-8")
