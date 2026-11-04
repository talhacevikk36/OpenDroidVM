"""GitHub Pages sitesi uretir: python tools/build_site.py -> site/index.html"""
import html
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
profiles = [json.loads(p.read_text(encoding="utf-8")) | {"id": p.stem}
            for p in sorted((root / "opendroidvm" / "profiles").glob("*.json"))]
rows = "\n".join(
    "<tr><td>{id}</td><td>{cn}</td><td>{name}</td><td>{soc}</td><td>{arch}</td><td>{ram}</td><td>{res}</td></tr>".format(
        id=html.escape(p["id"]), cn=html.escape(p.get("codename", "")),
        name=html.escape(p.get("name", "")), soc=html.escape(p.get("soc", "")),
        arch=p.get("arch", "aarch64"), ram=p.get("ram_mb", ""),
        res="{}x{}".format(p.get("screen", {}).get("width", ""), p.get("screen", {}).get("height", "")))
    for p in profiles)
page = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenDroidVM</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--bd:#ddd;--ac:#2563eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--mut:#999;--bd:#333;--ac:#6ea0ff}}}}
body{{font:16px/1.5 system-ui,sans-serif;margin:0;padding:1rem;background:var(--bg);color:var(--fg);max-width:960px;margin-inline:auto}}
code,pre{{background:rgba(127,127,127,.15);border-radius:6px}}code{{padding:.1em .3em}}pre{{padding:.8em;overflow-x:auto}}
input{{width:100%;box-sizing:border-box;padding:.6em;font-size:1em;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--fg)}}
.w{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9em}}th,td{{text-align:left;padding:.4em .6em;border-bottom:1px solid var(--bd);white-space:nowrap}}
a{{color:var(--ac)}}.m{{color:var(--mut)}}
</style></head><body>
<h1>OpenDroidVM</h1>
<p>Android cihaz profilleriyle QEMU uzerinde recovery ve ROM deneme araci. <b>{len(profiles)}</b> profil.</p>
<pre>pip install git+https://github.com/talhacevikk36/OpenDroidVM.git
odvm install-qemu
odvm run s10 --recovery twrp.img --mode fast</pre>
<p>Android (Termux): <code>bash scripts/install-termux.sh</code> &middot; <a href="https://github.com/talhacevikk36/OpenDroidVM">GitHub</a> &middot; <a href="https://github.com/talhacevikk36/OpenDroidVM/releases">Surumler</a></p>
<input id="q" placeholder="Cihaz ara (ad, kod adi, SoC)..." autofocus>
<div class="w"><table id="t"><thead><tr><th>ID</th><th>Kod adi</th><th>Ad</th><th>SoC</th><th>Mimari</th><th>RAM (MB)</th><th>Ekran</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="m">QEMU gercek SoC'leri taklit etmez; profiller CPU modeli, RAM ve ekran parametrelerini uygular.</p>
<script>
const q=document.getElementById('q'),rs=[...document.querySelectorAll('#t tbody tr')];
q.addEventListener('input',()=>{{const v=q.value.toLowerCase();rs.forEach(r=>r.style.display=r.textContent.toLowerCase().includes(v)?'':'none')}});
</script></body></html>"""
out = root / "site"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
print("site/index.html", len(profiles), "profil")
