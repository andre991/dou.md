"""Acesso à "Base de Dados de Publicações do DOU" (dados abertos da Imprensa Nacional).

A página https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados lista, para cada
ano e mês, um .zip por seção (ex.: S01082026.zip) com um XML por matéria. Não precisa de login.
"""
import re
import time
import urllib.parse
import urllib.request
from html import unescape

URL_BASE = "https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados"
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]
USER_AGENT = "dou.md/0.1 (+https://github.com/andre991/dou.md)"
ANO_INICIAL = 2002

RE_LINK_ZIP = re.compile(r"""href\s*=\s*["']([^"']+?\.zip[^"']*)["']""", re.I)
# S01082026.zip, S02082026.zip, S03082026.zip, S01082026E.zip (variações aceitas)
RE_NOME_ZIP = re.compile(r"(S\d{2}[A-Z]?)(\d{2})(\d{4})([A-Z0-9_-]*)\.zip", re.I)


def _get(url, metodo="GET", tentativas=4, timeout=120):
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, method=metodo, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), (r.read() if metodo == "GET" else b"")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, dict(e.headers or {}), b""
            erro = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            erro = e
        time.sleep(2 ** i * 3)
    raise RuntimeError(f"falha ao acessar {url}: {erro}")


def url_listagem(ano, mes):
    q = urllib.parse.urlencode({"ano": ano, "mes": MESES[mes - 1]})
    return f"{URL_BASE}?{q}"


def extrair_zips(html, url_pagina):
    """Extrai da página os links de .zip. Devolve lista de dicts {arquivo, secao, url}."""
    vistos, itens = set(), []
    for href in RE_LINK_ZIP.findall(html):
        url = urllib.parse.urljoin(url_pagina, unescape(href))
        nome = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
        m = RE_NOME_ZIP.search(nome) or RE_NOME_ZIP.search(urllib.parse.unquote(url))
        secao = (m.group(1).upper() + (m.group(4) or "").upper()) if m else nome.rsplit(".", 1)[0]
        arquivo = m.group(0) if m else nome
        if arquivo in vistos:
            continue
        vistos.add(arquivo)
        itens.append({"arquivo": arquivo, "secao": secao, "url": url})
    return itens


def listar_mes(ano, mes):
    """Lista os .zip disponíveis para um mês, com tamanho (Content-Length) quando informado."""
    url = url_listagem(ano, mes)
    status, _, corpo = _get(url)
    if status != 200:
        return []
    itens = extrair_zips(corpo.decode("utf-8", "replace"), url)
    for it in itens:
        try:
            st, cab, _ = _get(it["url"], metodo="HEAD", tentativas=2, timeout=60)
            tamanho = {k.lower(): v for k, v in cab.items()}.get("content-length")
            it["bytes"] = int(tamanho) if st == 200 and tamanho else None
        except RuntimeError:
            it["bytes"] = None
    return itens


def baixar(url, destino):
    status, _, corpo = _get(url, timeout=600)
    if status != 200:
        raise RuntimeError(f"download falhou ({status}): {url}")
    with open(destino, "wb") as f:
        f.write(corpo)
    return len(corpo)
