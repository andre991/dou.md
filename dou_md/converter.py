"""Conversão dos XMLs do DOU (formato INLABS / Base de Dados da Imprensa Nacional) para Markdown.

Cada XML traz uma matéria (`<article>`). A saída é um .md por matéria, com frontmatter YAML,
no caminho relativo AAAA/MM/DD/<secao>/<idMateria>-<slug>.md.
"""
import re, sys, zipfile, unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET
from html.parser import HTMLParser

SECOES = {"DO1": "secao-1", "DO2": "secao-2", "DO3": "secao-3",
          "DO1E": "secao-1-extra", "DO2E": "secao-2-extra", "DO3E": "secao-3-extra"}

class HtmlParaMd(HTMLParser):
    """Conversor mínimo do HTML do campo <Texto> para Markdown (parágrafos, negrito, tabelas)."""
    def __init__(self):
        super().__init__(); self.out=[]; self.buf=[]; self.tabela=None; self.linha=None; self.cel=None
    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "") or ""
        if tag == "table": self.tabela = []
        elif tag == "tr" and self.tabela is not None: self.linha = []
        elif tag in ("td", "th") and self.linha is not None: self.cel = []
        elif tag in ("b", "strong"): self._w("**")
        elif tag in ("i", "em"): self._w("_")
        elif tag == "br": self._w(" ")
        elif tag == "p": self._flush(); self._pref = "## " if "identifica" in cls else ""
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cel is not None:
            self.linha.append(" ".join("".join(self.cel).split()).replace("|", "\\|")); self.cel=None
        elif tag == "tr" and self.linha is not None: self.tabela.append(self.linha); self.linha=None
        elif tag == "table" and self.tabela is not None: self._flush(); self.out.append(self._tab(self.tabela)); self.tabela=None
        elif tag in ("b", "strong"): self._w("**")
        elif tag in ("i", "em"): self._w("_")
        elif tag == "p": self._flush()
    def handle_data(self, d): self._w(d)
    def _w(self, s):
        (self.cel if self.cel is not None else self.buf).append(s)
    def _flush(self):
        t = " ".join("".join(self.buf).split()).replace("** **", " ").replace("****", "")
        if t: self.out.append(getattr(self, "_pref", "") + t)
        self.buf=[]; self._pref=""
    @staticmethod
    def _tab(rows):
        if not rows: return ""
        n = max(len(r) for r in rows); rows=[r+[""]*(n-len(r)) for r in rows]
        md = ["| "+" | ".join(rows[0])+" |", "|"+"---|"*n]
        md += ["| "+" | ".join(r)+" |" for r in rows[1:]]
        return "\n".join(md)
    def resultado(self):
        self._flush(); return "\n\n".join(self.out)

def html_md(html):
    p = HtmlParaMd(); p.feed(html or ""); return p.resultado()

def slug(s, n=60):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:n].strip("-") or "materia"

def yaml_str(v):
    v = (v or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{v}"'

def converter_article(xml_bytes):
    raiz = ET.fromstring(xml_bytes)
    art = raiz if raiz.tag == "article" else raiz.find(".//article")
    a = art.attrib; body = art.find("body")
    campo = lambda t: (body.findtext(t) or "").strip() if body is not None else ""
    data = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (a.get("pubDate") or "").strip())
    if not data:
        raise ValueError(f"pubDate inválido: {a.get('pubDate')!r}")
    d, m, y = data.groups()
    meta = {
        "id": a.get("id"), "id_materia": a.get("idMateria"), "titulo": campo("Identifica") or a.get("name"),
        "tipo": a.get("artType"), "secao": a.get("pubName"), "data_publicacao": f"{y}-{m}-{d}",
        "edicao": a.get("editionNumber"), "pagina": a.get("numberPage"), "orgao": a.get("artCategory"),
        "ementa": campo("Ementa"), "url_pdf": a.get("pdfPage"),
        "fonte": "Imprensa Nacional - Diário Oficial da União",
    }
    fm = ["---"] + [f"{k}: {yaml_str(v)}" for k, v in meta.items() if v] + ["---", ""]
    corpo = html_md(campo("Texto"))
    if not corpo.startswith("## ") and meta["titulo"]:
        corpo = f"## {meta['titulo']}\n\n" + corpo
    if meta["orgao"]: corpo = f"> **Órgão:** {meta['orgao'].replace('/', ' › ')}\n\n" + corpo
    md = "\n".join(fm) + f"# {meta['tipo'] or 'Matéria'} — DOU {d}/{m}/{y}\n\n" + corpo.strip() + "\n"
    caminho = Path(y, m, d, SECOES.get(meta["secao"], slug(meta["secao"] or "outros")),
                   f"{slug(meta['id_materia'] or meta['id'] or '', 30)}-{slug(meta['titulo'] or '')}.md")
    return caminho, md

def iter_xml(origem):
    p = Path(origem)
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.lower().endswith(".xml"): yield n, z.read(n)
    elif p.is_dir():
        for f in sorted(p.rglob("*.xml")): yield str(f), f.read_bytes()
    else: yield str(p), p.read_bytes()

def converter_origem(origem, saida):
    """Converte todos os XMLs de um .zip, pasta ou arquivo. Devolve (convertidas, falhas, datas)."""
    ok = falhas = 0
    datas = set()
    for nome, dados in iter_xml(origem):
        try:
            rel, md = converter_article(dados)
            destino = Path(saida, rel)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(md, encoding="utf-8")
            datas.add("-".join(rel.parts[:3]))
            ok += 1
        except Exception as e:  # noqa: BLE001 - registramos e seguimos
            falhas += 1
            print(f"falha em {nome}: {e}", file=sys.stderr)
    return ok, falhas, sorted(datas)
