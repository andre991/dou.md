"""Linha de comando do dou.md.

    python -m dou_md mapear [--de AAAA-MM] [--ate AAAA-MM]
    python -m dou_md migrar [--mes AAAA-MM ...] [--pendentes N] [--publicar] [--janela 12]
    python -m dou_md progresso
    python -m dou_md podar [--janela 12]
    python -m dou_md converter <zip|pasta|xml> <saida>
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from . import converter, fonte, inventario, progresso

DADOS = Path("dados")


def _meses(de, ate):
    a, m = de
    while (a, m) <= ate:
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def _parse_mes(s):
    a, m = s.split("-")
    return int(a), int(m)


def _mes_atual():
    h = date.today()
    return h.year, h.month


def _na_janela(ano, mes, janela):
    a, m = _mes_atual()
    return (a * 12 + m) - (ano * 12 + mes) < janela


def cmd_mapear(args):
    linhas = inventario.carregar()
    de = _parse_mes(args.de) if args.de else (fonte.ANO_INICIAL, 1)
    ate = _parse_mes(args.ate) if args.ate else _mes_atual()
    total_novos = 0
    for ano, mes in _meses(de, ate):
        itens = fonte.listar_mes(ano, mes)
        novos = inventario.registrar_mapeamento(linhas, ano, mes, itens)
        total_novos += novos
        print(f"{ano}-{mes:02d}: {len(itens)} arquivo(s) na fonte, {novos} novo(s)")
        inventario.salvar(linhas)  # salva a cada mês, para não perder progresso
    print(f"mapeamento concluído: {total_novos} arquivo(s) novo(s), {len(linhas)} no total")
    progresso.gerar(linhas)


def _publicar_release(ano, mes, secao, pasta_md):
    tag = f"dou-{ano}-{mes:02d}"
    nome = f"dou-{ano}-{mes:02d}-{secao}.zip"
    caminho = Path(tempfile.gettempdir(), nome)
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pasta_md.rglob("*.md")):
            z.write(f, f.relative_to(pasta_md))
    existe = subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0
    if not existe:
        subprocess.run(["gh", "release", "create", tag, "--title", f"DOU {mes:02d}/{ano}",
                        "--notes", f"Matérias do DOU de {mes:02d}/{ano} em Markdown, um .zip por seção."],
                       check=True)
    subprocess.run(["gh", "release", "upload", tag, str(caminho), "--clobber"], check=True)
    caminho.unlink()
    return tag


def migrar_item(linha, publicar, janela):
    ano, mes, secao = int(linha["ano"]), int(linha["mes"]), linha["secao"]
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp, "fonte.zip")
        fonte.baixar(linha["url"], zip_path)
        saida = Path(tmp, "md")
        ok, falhas, _ = converter.converter_origem(zip_path, saida)
        if ok == 0:
            raise RuntimeError(f"nenhuma matéria convertida ({falhas} falhas)")
        if publicar:
            linha["release"] = _publicar_release(ano, mes, secao, saida)
        if _na_janela(ano, mes, janela):
            for f in saida.rglob("*.md"):
                destino = DADOS / f.relative_to(saida)
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, destino)
    linha.update({"status": "migrado", "materias": ok, "falhas": falhas, "migrado_em": inventario.agora()})
    return ok, falhas


def cmd_migrar(args):
    linhas = inventario.carregar()
    if args.mes:
        alvos = [l for l in linhas.values() if f"{l['ano']}-{l['mes']}" in args.mes]
        if not args.forcar:
            alvos = [l for l in alvos if l.get("status") != "migrado"]
    else:
        pend = [l for l in linhas.values() if l.get("status") != "migrado"]
        # do mais recente para o mais antigo: o que é mais útil primeiro
        alvos = sorted(pend, key=inventario.chave, reverse=True)[: args.pendentes]
    erros = 0
    for l in alvos:
        rotulo = f"{l['ano']}-{l['mes']} {l['secao']}"
        try:
            ok, falhas = migrar_item(l, args.publicar, args.janela)
            print(f"{rotulo}: {ok} matérias convertidas, {falhas} falhas")
        except Exception as e:  # noqa: BLE001
            erros += 1
            l["status"] = "falha"
            print(f"{rotulo}: FALHA - {e}", file=sys.stderr)
        inventario.salvar(linhas)
    progresso.gerar(linhas)
    print(f"{len(alvos)} arquivo(s) processado(s), {erros} com erro")


def cmd_progresso(_args):
    progresso.gerar(inventario.carregar())


def cmd_podar(args):
    """Tira de dados/ os meses fora da janela, desde que já estejam publicados nas Releases."""
    linhas = inventario.carregar()
    for pasta_ano in sorted(DADOS.glob("[0-9][0-9][0-9][0-9]")):
        for pasta_mes in sorted(pasta_ano.glob("[0-9][0-9]")):
            ano, mes = int(pasta_ano.name), int(pasta_mes.name)
            if _na_janela(ano, mes, args.janela):
                continue
            do_mes = [l for l in linhas.values() if int(l["ano"]) == ano and int(l["mes"]) == mes]
            if do_mes and all(l.get("status") == "migrado" and l.get("release") for l in do_mes):
                shutil.rmtree(pasta_mes)
                print(f"removido de dados/: {ano}-{mes:02d} (está nas Releases)")


def cmd_converter(args):
    ok, falhas, _ = converter.converter_origem(args.origem, args.saida)
    print(f"{ok} matérias convertidas, {falhas} falhas")


def main(argv=None):
    p = argparse.ArgumentParser(prog="dou_md")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("mapear", help="lista os arquivos disponíveis na fonte")
    s.add_argument("--de"); s.add_argument("--ate"); s.set_defaults(f=cmd_mapear)
    s = sub.add_parser("migrar", help="baixa e converte arquivos mapeados")
    s.add_argument("--mes", action="append", help="AAAA-MM (pode repetir)")
    s.add_argument("--pendentes", type=int, default=1, help="quantos pendentes migrar (sem --mes)")
    s.add_argument("--forcar", action="store_true", help="migra de novo mesmo se já migrado")
    s.add_argument("--publicar", action="store_true", help="publica o .zip de Markdown nas Releases")
    s.add_argument("--janela", type=int, default=12, help="meses mantidos em dados/")
    s.set_defaults(f=cmd_migrar)
    s = sub.add_parser("progresso", help="regera o PROGRESS.md"); s.set_defaults(f=cmd_progresso)
    s = sub.add_parser("podar", help="remove de dados/ meses fora da janela")
    s.add_argument("--janela", type=int, default=12); s.set_defaults(f=cmd_podar)
    s = sub.add_parser("converter", help="converte um zip/pasta/xml local")
    s.add_argument("origem"); s.add_argument("saida"); s.set_defaults(f=cmd_converter)
    args = p.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
