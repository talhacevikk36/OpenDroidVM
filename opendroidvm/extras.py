"""Small utilities: launch scripts, profile cloning, cleanup, shell completion."""
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from . import paths, profiles


def write_script(cmd, path):
    """Write the QEMU command as .bat/.cmd (Windows) or an executable shell script."""
    path = Path(path)
    if path.suffix.lower() in (".bat", ".cmd"):
        path.write_text("@echo off\r\n" + subprocess.list2cmdline([str(c) for c in cmd]) + "\r\n",
                        encoding="utf-8")
    else:
        path.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(str(c)) for c in cmd) + "\n",
                        encoding="utf-8")
        path.chmod(0o755)
    return path


def clone(src_id, new_id, name=None, ram=0, cores=0):
    src = profiles.find(src_id)
    if not src or not profiles.SAFE_ID.match(new_id) or new_id.startswith("."):
        return None
    base = profiles.PROFILE_DIR / f"{src.id}.json"
    ufile = profiles.user_dir() / f"{src.id}.json"
    j = json.loads((ufile if ufile.is_file() else base).read_text(encoding="utf-8"))
    j["name"] = name or f"{src.name} (copy)"
    if ram:
        j["ram_mb"] = ram
    if cores:
        j["cpu_cores"] = cores
    dest = profiles.user_dir() / f"{new_id.lower()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(j, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest


def dir_size(p):
    p = Path(p)
    if not p.exists():
        return 0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def clean_targets(include_recovery):
    from . import recovery
    t = [("cache", paths.cache_root())]
    if include_recovery:
        t.append(("recovery", recovery.default_dir()))
    return t


def clean(include_recovery=False, dry_run=False):
    """[(label, path, bytes)] of what was (or would be) removed."""
    out = []
    for label, p in clean_targets(include_recovery):
        size = dir_size(p)
        out.append((label, p, size))
        if not dry_run and Path(p).exists():
            shutil.rmtree(p, ignore_errors=True)
    return out


def completion(shell, commands, devices):
    cmds, devs = " ".join(sorted(commands)), " ".join(devices)
    dev_cmds = "info run start check clone fetch-recovery export avd"
    if shell in ("bash", "zsh"):
        pre = "autoload -U +X bashcompinit && bashcompinit\n" if shell == "zsh" else ""
        return f"""{pre}_odvm() {{
  local cur="${{COMP_WORDS[COMP_CWORD]}}" cmd="${{COMP_WORDS[1]}}"
  if [ "$COMP_CWORD" -eq 1 ]; then COMPREPLY=($(compgen -W "{cmds}" -- "$cur")); return; fi
  case " {dev_cmds} " in *" $cmd "*) COMPREPLY=($(compgen -W "{devs}" -- "$cur"));; esac
}}
complete -F _odvm odvm opendroidvm
"""
    if shell == "powershell":
        cl = ", ".join(f"'{c}'" for c in sorted(commands))
        dl = ", ".join(f"'{d}'" for d in devices)
        return f"""Register-ArgumentCompleter -Native -CommandName odvm,opendroidvm -ScriptBlock {{
  param($word, $ast, $pos)
  $parts = $ast.ToString().Split(' ')
  $list = if ($parts.Count -le 2) {{ @({cl}) }} else {{ @({dl}) }}
  $list | Where-Object {{ $_ -like "$word*" }} | ForEach-Object {{ [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }}
}}
"""
    return None
