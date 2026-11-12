"""Genera il sito DDRUG in docs/ a partire da content/ e templates/.
Uso: python3 build.py   (richiede jinja2 e pyyaml)"""
import re, shutil, sys, pathlib, unicodedata, yaml
from jinja2 import Environment, FileSystemLoader

R = pathlib.Path(__file__).parent
OUT = R / "docs"
GRUPPI = [("Docenti e ricercatori", True, False), ("Post-doc", False, False),
          ("Dottorandi", False, False), ("Alumni", True, True)]

GRUPPI_CORSI = [("Master", "master"), ("Corsi di perfezionamento", "perfezionamento"),
                ("Aggiornamento e formazione continua", "")]
DATI_CORSO = [("Coordinamento", "coordinatore"), ("Crediti", "cfu"), ("Ore", "ore"), ("Date", "date"),
              ("Scadenza iscrizioni", "scadenza"), ("In collaborazione con", "partner")]

def slug(testo):
    t = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60].strip("-")

def prepara_corsi(corsi):
    gruppi = [{"nome": n, "corsi": []} for n, _ in GRUPPI_CORSI]
    for c in corsi:
        c["slug"] = slug(c["titolo"])
        c["dati"] = [(et, f"{c[k]} CFU" if k == "cfu" else c[k]) for et, k in DATI_CORSO if c.get(k)]
        i = next(i for i, (_, chiave) in enumerate(GRUPPI_CORSI) if chiave in c.get("tipo", "").lower())
        gruppi[i]["corsi"].append(c)
    return [g for g in gruppi if g["corsi"]]

def dimensioni(jpg):
    """Larghezza e altezza di un JPEG, senza librerie esterne."""
    d = jpg.read_bytes(); i = 2
    while i < len(d):
        m, n = d[i + 1], int.from_bytes(d[i + 2:i + 4], "big")
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
        i += 2 + n
    return "", ""

def carica(nome):
    return yaml.safe_load((R / "content" / nome).read_text(encoding="utf-8"))

def visibile(x):
    return str(x.get("mostra", "sì")).strip().lower() in ("sì", "si", "yes")

def main():
    persone = [p for p in carica("persone.yml")["persone"] if visibile(p) and p.get("gruppo")]
    corsi = [c for c in carica("formazione.yml")["corsi"] if visibile(c) and "verificare" not in c.get("tipo", "").lower()]
    profili = {}
    for f in sorted((R / "content" / "profili").glob("*.yml")):
        prof = yaml.safe_load(f.read_text(encoding="utf-8"))
        base = next((x for x in persone if x["nome"] == prof["nome"]), None)
        if base is None:
            sys.exit(f"Profilo {f.name}: {prof['nome']} non è tra le persone visibili in persone.yml")
        prof = {**base, **prof}
        if prof.get("foto"):
            if not (R / "assets" / "persone" / prof["foto"]).exists():
                sys.exit(f"Profilo {f.name}: manca la foto assets/persone/{prof['foto']}")
            prof["foto_w"], prof["foto_h"] = dimensioni(R / "assets" / "persone" / prof["foto"])
        base["pagina"] = f.stem + ".html"
        profili[base["pagina"]] = prof
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
    comuni = dict(gruppi=gruppi, corsi=corsi, ricerca=ricerca, gruppi_corsi=prepara_corsi(corsi),
                  n_docenti=sum(p["gruppo"] == "Docenti e ricercatori" for p in persone),
                  n_giovani=sum(p["gruppo"] in ("Post-doc", "Dottorandi") for p in persone))
    pagine = {"index.html": ("home.html", "home"), "formazione.html": ("formazione.html", "formazione")}
    resa = {out: env.get_template(tpl).render(pagina=nome, **comuni) for out, (tpl, nome) in pagine.items()}
    for out, prof in profili.items():
        resa[out] = env.get_template("persona.html").render(pagina="persona", p=prof, **comuni)
    heta = carica("heta-lab.yml")
    visibili = {x["nome"]: x for x in persone}
    citati = [x["nome"] for x in heta["persone"]] + [n for pr in heta["progetti"] for n in pr.get("persone", [])]
    assenti = sorted(set(citati) - set(visibili))
    if assenti:
        sys.exit(f"heta-lab.yml cita persone non visibili in persone.yml: {assenti}")
    for x in heta["persone"]:
        x["pagina"] = visibili[x["nome"]].get("pagina")
    resa["heta-lab.html"] = env.get_template("heta-lab.html").render(pagina="heta", h=heta, **comuni)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for out, html in resa.items():
        (OUT / out).write_text(html, encoding="utf-8")
    shutil.copytree(R / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")
    print(f"OK: {len(persone)} persone, {len(corsi)} corsi, {len(resa)} pagine")

if __name__ == "__main__":
    main()
