"""Inventário de todos os arquivos do DOU: o que foi mapeado na fonte e o que já foi migrado.

Fica em estado/inventario.csv (uma linha por .zip de mês/seção) e é a base do PROGRESS.md.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

ARQUIVO = Path("estado/inventario.csv")
CAMPOS = ["ano", "mes", "secao", "arquivo", "url", "bytes", "mapeado_em",
          "status", "materias", "falhas", "migrado_em", "release"]
# status: mapeado (ainda não migrado) | migrado | falha


def agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def chave(linha):
    return (int(linha["ano"]), int(linha["mes"]), linha["secao"])


def carregar(caminho=ARQUIVO):
    if not Path(caminho).exists():
        return {}
    with open(caminho, newline="", encoding="utf-8") as f:
        return {chave(l): l for l in csv.DictReader(f)}


def salvar(linhas, caminho=ARQUIVO):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        for k in sorted(linhas):
            w.writerow({c: linhas[k].get(c, "") for c in CAMPOS})


def registrar_mapeamento(linhas, ano, mes, itens):
    """Acrescenta/atualiza os arquivos encontrados num mês. Não apaga o status de migração."""
    novos = 0
    for it in itens:
        k = (ano, mes, it["secao"])
        atual = linhas.get(k)
        if atual is None:
            linhas[k] = {"ano": ano, "mes": f"{mes:02d}", "secao": it["secao"], "arquivo": it["arquivo"],
                         "url": it["url"], "bytes": it.get("bytes") or "", "mapeado_em": agora(),
                         "status": "mapeado"}
            novos += 1
        else:
            mudou = str(atual.get("bytes") or "") != str(it.get("bytes") or "")
            atual.update({"arquivo": it["arquivo"], "url": it["url"], "bytes": it.get("bytes") or ""})
            if mudou and atual.get("status") == "migrado":
                # A Imprensa Nacional regrava o .zip do mês corrente: precisa migrar de novo.
                atual["status"] = "mapeado"
    return novos
