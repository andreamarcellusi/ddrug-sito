"""Genera il sito DDRUG in docs/ a partire da content/ e templates/.
Uso: python3 build.py   (richiede jinja2 e pyyaml)"""
import shutil, sys, pathlib, yaml
from jinja2 import Environment, FileSystemLoader

R = pathlib.Path(__file__).parent
OUT = R / "docs"
GRUPPI = [("Docenti e ricercatori", True, False), ("Post-doc", False, False),
          ("Dottorandi", False, False), ("Alumni", True, True)]

def carica(nome):
    return yaml.safe_load((R / "content" / nome).read_text(encoding="utf-8"))

def visibile(x):
    return str(x.get("mostra", "sì")).strip().lower() in ("sì", "si", "yes")

def main():
    persone = [p for p in carica("persone.yml")["persone"] if visibile(p) and p.get("gruppo")]
    corsi = [c for c in carica("formazione.yml")["corsi"] if visibile(c) and "verificare" not in c.get("tipo", "").lower()]
    gruppi = []
    for nome, largo, alumni in GRUPPI:
        membri = [p for p in persone if p["gruppo"] == nome]
        if membri:
            gruppi.append({"nome": nome, "largo": largo, "alumni": alumni, "persone": membri})
    sconosciuti = {p["gruppo"] for p in persone} - {g[0] for g in GRUPPI}
    if sconosciuti:
        sys.exit(f"Gruppo non previsto in persone.yml: {sconosciuti}")
    ricerca = carica("ricerca.yml")
    env = Environment(loader=FileSystemLoader(R / "templates"), autoescape=True)
    html = env.get_template("home.html").render(
        gruppi=gruppi, corsi=corsi, ricerca=ricerca,
        n_docenti=sum(p["gruppo"] == "Docenti e ricercatori" for p in persone),
        n_giovani=sum(p["gruppo"] in ("Post-doc", "Dottorandi") for p in persone))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(html, encoding="utf-8")
    shutil.copytree(R / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")
    print(f"OK: {len(persone)} persone, {len(corsi)} corsi")

if __name__ == "__main__":
    main()
