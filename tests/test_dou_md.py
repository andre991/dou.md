from pathlib import Path

from dou_md import converter, fonte, inventario, progresso

FIX = Path(__file__).parent / "fixtures"


def test_converte_materia():
    rel, md = converter.converter_article((FIX / "exemplo.xml").read_bytes())
    assert rel.as_posix() == "2026/11/27/secao-1/98765432-portaria-mf-no-123-de-26-de-novembro-de-2026.md"
    assert md.startswith("---\nid: \"12345678\"")
    assert 'data_publicacao: "2026-11-27"' in md
    assert "O **MINISTRO DE ESTADO DA FAZENDA**" in md
    assert "| A | R$ 10,00 |" in md


def test_converter_origem(tmp_path):
    ok, falhas, datas = converter.converter_origem(FIX / "exemplo.xml", tmp_path)
    assert (ok, falhas, datas) == (1, 0, ["2026-11-27"])


def test_extrair_zips():
    html = '''<a href="/documents/49035712/0/S01082026.zip/abc?version=1.0">Seção 1</a>
              <a href='https://www.in.gov.br/documents/1/S02082026.zip'>2</a>
              <a href="/documents/1/S01082026.zip/abc?version=1.0">dup</a>
              <a href="/outro.pdf">pdf</a>'''
    itens = fonte.extrair_zips(html, fonte.url_listagem(2026, 8))
    assert [(i["arquivo"], i["secao"]) for i in itens] == [("S01082026.zip", "S01"), ("S02082026.zip", "S02")]
    assert itens[0]["url"].startswith("https://www.in.gov.br/documents/49035712/")


def test_url_listagem():
    assert fonte.url_listagem(2026, 3) == fonte.URL_BASE + "?ano=2026&mes=Mar%C3%A7o"


def test_inventario_e_progresso(tmp_path):
    linhas = {}
    itens = [{"arquivo": "S01082026.zip", "secao": "S01", "url": "u1", "bytes": 10},
             {"arquivo": "S02082026.zip", "secao": "S02", "url": "u2", "bytes": 20}]
    assert inventario.registrar_mapeamento(linhas, 2026, 8, itens) == 2
    linhas[(2026, 8, "S01")].update(status="migrado", materias=8590)
    csv = tmp_path / "inv.csv"
    inventario.salvar(linhas, csv)
    linhas = inventario.carregar(csv)
    # o .zip mudou de tamanho na fonte: volta a pendente
    itens[0]["bytes"] = 11
    inventario.registrar_mapeamento(linhas, 2026, 8, itens)
    assert linhas[(2026, 8, "S01")]["status"] == "mapeado"
    linhas[(2026, 8, "S01")]["status"] = "migrado"
    out = tmp_path / "PROGRESS.md"
    progresso.gerar(linhas, out)
    texto = out.read_text()
    assert "**50.0%**" in texto
    assert "| Agosto | 50% | 1 / 2 | S01 | S02 | 8.590 |" in texto
