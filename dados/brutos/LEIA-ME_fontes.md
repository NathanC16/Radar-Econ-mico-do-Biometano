# Fontes brutas — origem e data de coleta

| Arquivo | Origem | Coleta |
|---|---|---|
| `iepuc_boletim_ago2026.pdf` (+ `.txt` extraídos com `pdftotext`) | https://www.iepuc.puc-rio.br/arquivos/boletim-biometano/08_Boletim_Biometano_IEPUC_ago_2026.pdf — Ed. Nº 2, publicado em 28/09/2026 | 01/10/2026 (conferido byte a byte em 02/10/2026) |
| `iepuc_boletim_jul2026.pdf` (+ `.txt`) | https://www.iepuc.puc-rio.br/arquivos/boletim-biometano/07_Boletim_Biometano_IEPUC_jul_2026.pdf — Ed. Nº 1 (usado para comparar as revisões entre edições) | 02/10/2026 |
| `panorama_biometano_goias_sgg_2026.pdf` / `.txt` | Governo de Goiás (SGG) / CBIE Advisory — *Panorama do Biometano em Goiás* (2026), estudo do PEEG 2030: https://goias.gov.br/governo/wp-content/uploads/sites/11/2026/02/Panorama-do-Biometano-em-Goias.pdf (seções 6.2–6.4: plantas e potencial de biogás por fonte e município) | 02/10/2026 |
| `case-ceasa-goias.html` / `.txt` | https://www.4watt.tech/case-ceasa-goias.html | 01/10/2026 |
| `case-utb-franca.html` / `.txt` | https://www.4watt.tech/case-utb-franca.html | 01/10/2026 |
| `4watt-home.html` / `.txt` | https://www.4watt.tech/ — seção de cases (Frigorífico Franca, Organo Buritis) | 02/10/2026 |
| `4watt-solucao-biogas.html` / `.txt` | https://www.4watt.tech/solucao-biogas.html — Frigorífico Franca (2.800 Nm³/dia) | 02/10/2026 |
| `anp_abertos/` | ANP — Dados Abertos de Biometano (zip com 2 CSVs) — ver `anp_abertos/PROVENIENCIA.md` | 02/10/2026 |
| `anp_precos/mensal-estados-desde-jan2013.xlsx` (não versionado; baixado por `dados/preparar_precos_anp.py`) | https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/mensal/mensal-estados-desde-jan2013.xlsx | 02/10/2026 |
| `ibge/ppm_2025.json`, `ibge/ppm_2023.json` | IBGE — API SIDRA, tabelas 3939 (rebanhos) e 94 (vacas ordenhadas), gerados por `dados/preparar_ibge.py` | 02/10/2026 |
| `brazil-states.geojson` | https://github.com/codeforamerica/click_that_hood/blob/master/public/data/brazil-states.geojson | 01/10/2026 |
| `links_4watt.txt` | Links internos do site 4watt.tech (mapa das páginas consultadas) | 01/10/2026 |

Obs.: os PDFs não são versionados no Git (são públicos e baixáveis pelos links acima); ficam no repositório os textos extraídos, usados na validação. O texto do Panorama de Goiás também fica de fora (copyright CBIE — ver `.gitignore`): baixe o PDF pelo link e extraia com `pdftotext -layout` para rodar as checagens literais.

Obs.: as URLs dos cases exigem o sufixo `.html` (sem ele o site retorna 404).
