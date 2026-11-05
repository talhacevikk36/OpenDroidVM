"""Tiny prompt helpers (easy to test: they only use input())."""
YES = ("y", "yes", "e", "evet", "1")


def ask(prompt, default=""):
    try:
        s = input(prompt)
    except EOFError:
        return default
    s = s.strip()
    return s if s else default


def yes(prompt, default=True):
    s = ask(prompt, "").lower()
    return default if not s else s in YES


def pick(prompt, count, default=None):
    """Ask for a number in 1..count (0 allowed). Returns int, or None on bad input."""
    s = ask(prompt, "" if default is None else str(default))
    if s.isdigit() and 0 <= int(s) <= count:
        return int(s)
    return None
