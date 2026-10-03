# Radar Econômico do Biometano — Dashboard analítico

**Projeto Integrador V-A** · PUC-Goiás · Curso de Big Data e Inteligência Artificial
**Organização parceira (extensão):** 4WaTT Bio Engenharia S/A — Goiânia/GO

Dashboard open source (Python) para leitura estruturada do mercado brasileiro de
biogás/biometano e posicionamento dos projetos públicos da 4WaTT no contexto nacional,
apoiando decisões comerciais/técnicas (priorização de substratos e regiões, narrativa
de viabilidade e comunicação a investidores).

## Como rodar

```bash
cd pi5a-biometano-4watt
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run streamlit_app.py --server.headless true --server.port 8599
# abrir: http://localhost:8599
```

Outros comandos (a partir da raiz do projeto):

```bash
.venv/bin/python dados/preparar_anp.py            # (re)gera as bases da ANP a partir dos CSVs brutos
.venv/bin/python dados/preparar_precos_anp.py     # preços de combustíveis por estado (ANP)
.venv/bin/python dados/preparar_ibge.py 2025      # rebanhos por estado (IBGE) e potencial da pecuária
.venv/bin/python dados/preparar_cibiogas.py       # plantas de biogás por estado e no Brasil (CIBiogás)
.venv/bin/python notebook/validar_dados.py        # 91 verificações dos dados contra as fontes (7 exigem o PDF do estudo de Goiás, que fica fora do Git)
.venv/bin/python apresentacao/gerar_slides.py     # regera apresentacao/apresentacao_oral.pptx
.venv/bin/python -m ipykernel install --user --name pi5a   # kernel para abrir o notebook de EDA
```

## Publicar online (Streamlit Community Cloud)

1. Envie o repositório para o GitHub (o `.gitignore` já deixa de fora documentos pessoais,
   PDFs/planilhas brutas e arquivos gerados).
2. Em <https://share.streamlit.io>, **Create app** → escolha o repositório, branch `main`
   e o arquivo principal `streamlit_app.py`.
3. Em **Advanced settings**, selecione Python 3.13. Não há segredos a configurar:
   o painel lê apenas os CSVs de `dados/limpos/`.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `streamlit_app.py` | Ponto de entrada (usado pelo Streamlit Community Cloud); executa `app/app.py` |
| `app/app.py` | Aplicação Streamlit (7 abas + filtros; tema claro e escuro) |
| `dados/fontes.json` | Cadastro das fontes de dados (nome, link e CSVs de cada uma) — alimenta o filtro *Fontes de dados* do painel; para incluir uma fonte nova, basta cadastrá-la aqui |
| `dados/preparar_anp.py` | Gera as bases da ANP (por UF, por usina e série nacional) a partir dos dados abertos brutos |
| `dados/preparar_precos_anp.py` · `preparar_ibge.py` · `preparar_cibiogas.py` | Geram as bases de preços (ANP), rebanhos (IBGE) e plantas de biogás (CIBiogás) |
| `.streamlit/config.toml` | Tema visual do painel |
| `dados/brutos/` | Materiais brutos: boletins IEPUC (texto extraído), dados abertos da ANP, respostas da API do IBGE, textos da CIBiogás/ABEGÁS, páginas do site 4WaTT (HTML + texto), GeoJSON de estados (Code for America). Origem e data de coleta em `dados/brutos/LEIA-ME_fontes.md` |
| `dados/limpos/` | Bases estruturadas em CSV usadas pelo app + GeoJSON processado (`geojson_brasil_ufs.geojson`, com `id = sigla da UF`) |
| `notebook/01_exploracao.ipynb` | Análise exploratória (EDA) documentada, salva com as saídas |
| `notebook/validar_dados.py` | Validação programática das bases contra as fontes (91 verificações) |
| `relatorio/` | Relatório técnico (item 3.1 da proposta) |
| `apresentacao/` | Apresentação oral (item 3.4), gerada por `gerar_slides.py`; capturas do painel em `img/` |
| `documentos/` | Documentos comprobatórios extensionistas (carta, registros) — **fora do Git** (dados pessoais); só no zip de entrega |

## Fontes dos dados

- **IEPUC-PUC-Rio**, *Boletim Mensal de Acompanhamento da Indústria de Biometano no Brasil*,
  Agosto de 2026, Edição Nº 2 (publicado 28/09/2026) — com dados da ANP, MME e B3:
  https://www.iepuc.puc-rio.br/arquivos/boletim-biometano/08_Boletim_Biometano_IEPUC_ago_2026.pdf
- **ANP — Dados Abertos de Biometano** (produção por UF e capacidade por usina, 2020–2026):
  https://www.gov.br/anp/pt-br/assuntos/producao-e-fornecimento-de-biocombustiveis/biometano/biometano-dados-abertos.zip
  (leitura de unidades e validação cruzada em `dados/brutos/anp_abertos/PROVENIENCIA.md`)
- **ANP — Levantamento de Preços de Combustíveis** (série mensal por estado; diesel S10 e GNV):
  https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos
- **IBGE — Pesquisa da Pecuária Municipal** (rebanhos por estado, via API SIDRA, tabelas 3939 e 94):
  https://sidra.ibge.gov.br/tabela/3939 e https://sidra.ibge.gov.br/tabela/94
- **CIBiogás — Panorama do Biogás no Brasil** (levantamento BiogásMap): edição 2023 (Relatório
  Técnico nº 001/2024, licença CC BY 4.0):
  https://abiogas.com.br/wp-content/uploads/protectedfiles/Panorama%20do%20Biog%C3%A1s%202023%20-%20CIbiog%C3%A1s%20(2024).pdf ·
  edições 2024 e 2025 (e-book liberado só com cadastro; números divulgados pela ABEGÁS):
  https://www.abegas.org.br/arquivos/95755 · https://www.abegas.org.br/arquivos/99980
- **Governo de Goiás (SGG) / CBIE Advisory**, *Panorama do Biometano em Goiás* (2026), estudo do
  Plano Estadual de Energia de Goiás 2030:
  https://goias.gov.br/governo/wp-content/uploads/sites/11/2026/02/Panorama-do-Biometano-em-Goias.pdf
- **Site oficial da 4WaTT** (projetos públicos):
  https://www.4watt.tech/ (seção de cases: Frigorífico Franca, Organo Buritis) ·
  https://www.4watt.tech/solucao-biogas.html ·
  https://www.4watt.tech/case-ceasa-goias.html · https://www.4watt.tech/case-utb-franca.html
- **Malha GeoJSON dos estados brasileiros**:
  https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson

## Convenções e limitações (resumo)

- Unidade do boletim IEPUC: **Mm³/d = mil m³ por dia** (notação ANP/MME); o painel exibe "mil m³/d".
- Potencial de Goiás: estimativa **teórica** do estudo estadual (m³/ano), não produção viável.
- Base de transações do IEPUC-Rio não é exaustiva (compilada de notícias/relatórios públicos).
- Registro ANP cobre apenas contratos dentro da especificação regulatória.
- Plantas de biogás (CIBiogás): edição 2023 completa; das edições 2024 e 2025, só os números divulgados pela ABEGÁS (e-book exige cadastro).
- Dados da 4WaTT: exclusivamente informação pública do site oficial.
- Data de referência: **agosto/2026**.
