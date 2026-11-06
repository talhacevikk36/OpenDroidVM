__version__ = "0.9.1a1"      # PEP 440; alpha until a phone image really boots (then 1.0.0)


def display_version(v=None):
    """0.9.1a1 -> 0.9.1-alpha.1 (what people see and what GitHub tags look like)."""
    import re
    v = v or __version__
    m = re.match(r"^v?(\d+\.\d+\.\d+)(?:[-._]?(alpha|beta|rc|a|b)[-._]?(\d*))?$", v, re.I)
    if not m or not m.group(2):
        return v.lstrip("vV")
    name = {"a": "alpha", "b": "beta"}.get(m.group(2).lower(), m.group(2).lower())
    return f"{m.group(1)}-{name}.{m.group(3) or 1}"
