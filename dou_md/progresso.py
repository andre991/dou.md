"""Gera o PROGRESS.md a partir do inventário: % migrada por ano e por mês."""
from collections import defaultdict
from pathlib import Path

from .fonte import MESES
from .inventario import agora


def _pct(migrados, total):
    return (100.0 * migrados / total) if total else 0.0


def _barra(p, largura=20):
    cheio = round(p / 100 * largura)
    return "█" * cheio + "░" * (largura - cheio)


def _n(x):
    return f"{x:,}".replace(",", ".")


def _mb(b):
    return f"{_n(round(b / 1_048_576))} MB"


def gerar(linhas, caminho="PROGRESS.md"):
    por_ano = defaultdict(list)
    for l in linhas.values():
        por_ano[int(l["ano"])].append(l)

    def resumo(itens):
        total = len(itens)
        migr = sum(1 for i in itens if i.get("status") == "migrado")
        falhas = sum(1 for i in itens if i.get("status") == "falha")
        materias = sum(int(i.get("materias") or 0) for i in itens if i.get("status") == "migrado")
        tamanho = sum(int(i.get("bytes") or 0) for i in itens)
        return total, migr, falhas, materias, tamanho

    t, m, f, mat, tam = resumo(list(linhas.values()))
    p = _pct(m, t)
    out = [
        "# Progresso da migração do DOU para Markdown",
        "",
        f"_Atualizado automaticamente em {agora()} (UTC)._",
        "",
        "A porcentagem é `arquivos migrados / arquivos mapeados`, onde cada arquivo é o .zip de um mês e",
        "uma seção na [Base de Dados de Publicações do DOU](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados).",
        "",
        "## Total",
        "",
        f"`{_barra(p)}` **{p:.1f}%**",
        "",
        "| Mapeados | Migrados | Com falha | Matérias convertidas | Tamanho na fonte |",
        "|---:|---:|---:|---:|---:|",
        f"| {t} | {m} | {f} | {_n(mat)} | {_mb(tam)} |",
        "",
    ]
    if not linhas:
        out += ["Nenhum arquivo mapeado ainda. Rode o workflow **Mapear DOU** (ou `python -m dou_md mapear`).", ""]
        Path(caminho).write_text("\n".join(out), encoding="utf-8")
        return

    out += ["## Por ano", "", "| Ano | Progresso | % | Migrados / Mapeados | Matérias |", "|---|---|---:|---:|---:|"]
    for ano in sorted(por_ano, reverse=True):
        t, m, f, mat, _ = resumo(por_ano[ano])
        p = _pct(m, t)
        out.append(f"| [{ano}](#{ano}) | `{_barra(p, 10)}` | {p:.1f}% | {m} / {t} | {_n(mat)} |")
    out += ["", "## Por mês", ""]
    for ano in sorted(por_ano, reverse=True):
        por_mes = defaultdict(list)
        for l in por_ano[ano]:
            por_mes[int(l["mes"])].append(l)
        t, m, *_ = resumo(por_ano[ano])
        out += [f"### {ano}", "", f"<details{' open' if ano == max(por_ano) else ''}><summary>{ano}: {_pct(m, t):.1f}% ({m} de {t} arquivos)</summary>", "",
                "| Mês | % | Migrados / Mapeados | Seções migradas | Pendentes | Matérias |",
                "|---|---:|---:|---|---|---:|"]
        for mes in sorted(por_mes, reverse=True):
            itens = sorted(por_mes[mes], key=lambda i: i["secao"])
            t, m, f, mat, _ = resumo(itens)
            ok = ", ".join(i["secao"] for i in itens if i.get("status") == "migrado") or "-"
            pend = ", ".join(i["secao"] + (" (falha)" if i.get("status") == "falha" else "")
                             for i in itens if i.get("status") != "migrado") or "-"
            out.append(f"| {MESES[mes - 1]} | {_pct(m, t):.0f}% | {m} / {t} | {ok} | {pend} | {_n(mat)} |")
        out += ["", "</details>", ""]
    Path(caminho).write_text("\n".join(out), encoding="utf-8")
