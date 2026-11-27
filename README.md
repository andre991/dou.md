# dou.md

DOU.md: o Diário Oficial da União em Markdown, organizado para ser lido por IAs.

Todas as matérias do DOU viram arquivos `.md`, um por matéria, com metadados em YAML no topo. A fonte é a
[Base de Dados de Publicações do DOU](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados),
dados abertos da Imprensa Nacional (XML oficial, sem login).

O andamento da migração está em **[PROGRESS.md](PROGRESS.md)**.

## Onde estão os dados

| O quê | Onde |
|---|---|
| Últimos 12 meses | Pasta [`dados/`](dados/), em `AAAA/MM/DD/<seção>/<idMateria>-<título>.md` |
| Histórico completo | [Releases](../../releases): uma release por mês (`dou-AAAA-MM`), com um `.zip` de Markdown por seção |
| Inventário (o que existe na fonte e o que já foi migrado) | [`estado/inventario.csv`](estado/inventario.csv) |

O histórico inteiro tem centenas de GB, por isso não cabe no git: os meses antigos ficam nas Releases.

## Formato de cada matéria

```markdown
---
id: "12345678"
id_materia: "98765432"
titulo: "PORTARIA MF Nº 123, DE 26 DE NOVEMBRO DE 2026"
tipo: "Portaria"
secao: "DO1"
data_publicacao: "2026-11-27"
edicao: "226"
pagina: "45"
orgao: "Ministério da Fazenda/Gabinete do Ministro"
ementa: "Dispõe sobre ..."
url_pdf: "http://pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp?..."
fonte: "Imprensa Nacional - Diário Oficial da União"
---
# Portaria — DOU 27/11/2026

> **Órgão:** Ministério da Fazenda › Gabinete do Ministro

## PORTARIA MF Nº 123, DE 26 DE NOVEMBRO DE 2026

Texto da matéria, com negrito e tabelas em Markdown.
```

Seções: `secao-1` (atos normativos), `secao-2` (atos de pessoal), `secao-3` (contratos, editais e avisos) e
as edições extras (`secao-1-extra` etc.).

## Como funciona

| Workflow | Quando | O que faz |
|---|---|---|
| **Mapear DOU** | manual | Percorre a fonte de 2002 até hoje e registra cada `.zip` (mês × seção) em `estado/inventario.csv` |
| **Migrar histórico do DOU** | a cada 3 horas | Pega um lote de arquivos pendentes (do mais recente para o mais antigo), converte e publica nas Releases |
| **Bot diário do DOU** | todo dia, 13h de Brasília | Remapeia o mês atual e o anterior, converte o que mudou, atualiza `dados/` e o `PROGRESS.md` |

A Imprensa Nacional regrava o `.zip` do mês corrente todos os dias; quando o tamanho muda, o arquivo volta a
ficar pendente e é convertido de novo.

### Rodando localmente

```bash
python -m dou_md mapear --de 2026-08 --ate 2026-08   # mapeia um mês
python -m dou_md migrar --mes 2026-08                # baixa e converte
python -m dou_md progresso                           # regera o PROGRESS.md
python -m dou_md converter arquivo.zip saida/        # converte um .zip local
python -m pytest -q                                  # testes
```

Só usa a biblioteca padrão do Python (3.10+).

## Licença e uso

- Código: MIT (veja [LICENSE](LICENSE)).
- Conteúdo: atos oficiais não são protegidos por direito autoral (Lei 9.610/98, art. 8º, IV); a fonte é
  publicada pela Imprensa Nacional como dado aberto.
- As Seções 2 e 3 contêm nomes e outros dados pessoais publicados por força de lei. Quem reutilizar esses dados
  deve respeitar a LGPD (Lei 13.709/18), em especial a finalidade da publicação original.
- Este projeto não tem vínculo com a Imprensa Nacional. A versão oficial e válida é sempre a publicada em
  [in.gov.br](https://www.in.gov.br).
