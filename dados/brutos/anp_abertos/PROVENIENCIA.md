# Proveniência e qualidade dos dados — Fase 2

Acesso em **02/10/2026**.

## Fontes primárias

| Fonte | Arquivo bruto | URL |
|---|---|---|
| IEPUC-PUC-Rio, Boletim Biometano ago/2026 (Ed. 2) | `../iepuc_boletim_ago2026.pdf` → `iepuc_boletim.txt` | https://www.iepuc.puc-rio.br/arquivos/boletim-biometano/08_Boletim_Biometano_IEPUC_ago_2026.pdf |
| IEPUC-PUC-Rio, Boletim Biometano jul/2026 (Ed. 1 — primeira edição da série) | `../iepuc_boletim_jul2026.pdf` → `iepuc_boletim_jul2026.txt` | https://www.iepuc.puc-rio.br/arquivos/boletim-biometano/07_Boletim_Biometano_IEPUC_jul_2026.pdf |
| **ANP — Dados Abertos Biometano** (2 CSVs: capacidade por usina e produção por estado, jan/2020–ago/2026) | `anp_abertos/Biometano_DadosAbertos_CSV_{Capacidade,Producao}.csv` | https://www.gov.br/anp/pt-br/assuntos/producao-e-fornecimento-de-biocombustiveis/biometano/biometano-dados-abertos.zip |
| ANP — Painel Dinâmico de Produtores de Biometano (Power BI público; referência) | — | https://www.gov.br/anp/pt-br/centrais-de-conteudo/paineis-dinamicos-da-anp/paineis-e-mapa-dinamicos-de-produtores-de-combustiveis-e-derivados/painel-dinamico-de-produtores-de-biometano |

## ⚠️ Unidades — regras de leitura (revisadas em 02/10/2026, conferidas UF a UF)

> A versão anterior desta nota dizia que as colunas estavam em "mil m³". Conferindo estado por
> estado contra o boletim, as unidades **corretas** são as abaixo. Os números derivados estavam
> certos; só a descrição estava errada.

1. **ANP `Producao.csv`**: coluna "Produção (m³)" é o **volume do mês em m³**. Para obter
   mil m³/d: dividir pelos **dias reais do mês** e por 1.000. Ponto = separador decimal
   (`4324235.558`); valores pequenos como `173.037` (MG) são lidos como decimal, o que fecha o
   total nacional. **Somar os produtos BIOMETANO e BIOMETANO COMPRIMIDO** (SP e PR declaram parte
   da produção como comprimido) — sem isso, a série fica até 28 mil m³/d abaixo do boletim.
   Âncoras ago/26: CE 36,74 · PE 84,44 · RJ 139,49 · SP 177,60 · RS 85,64 · SC 5,14 · total 529,1
   (IEPUC: 37 · 84 · 139 · 178 · 86 · "Outros" 5 · 529).
2. **ANP `Capacidade.csv`**: "m³/d" está **correto** (vírgula decimal: `204000,00` = 204 mil m³/d).
   Âncora: soma das 21 usinas em ago/26 = 1.368,1 mil m³/d vs IEPUC 1.368.
3. **IEPUC**: Mm³/d = mil m³/d em todo o boletim.
4. **Correção (02/10/2026):** a série nacional anterior dividia fevereiro por 28 dias também em
   ano bissexto (fev/2020: 74,5 → 71,9; fev/2024: 233,3 → 225,3). As bases agora são geradas por
   `dados/preparar_anp.py`, que usa o calendário real.

## Validação cruzada ANP × IEPUC (série 2026)

| Mês | ANP (reconstruído) | IEPUC Ed.2 | Δ |
|---|---|---|---|
| 01/26 | 383,7 | 384 | −0,3 |
| 02/26 | 410,2 | 410 | +0,2 |
| 03/26 | 403,9 | 404 | −0,1 |
| 04/26 | 450,9 | 451 | −0,1 |
| 05/26 | 451,4 | 451 | +0,4 |
| 06/26 | 531,6 | 532 | −0,4 |
| 07/26 | 560,7 | 561 | −0,3 |
| 08/26 | 529,1 | 529 | +0,1 |

→ O CSV estadual da ANP é a fonte bruta do boletim IEPUC (concordância < ±0,5 Mm³/d).

## Divergências entre edições do IEPUC (registro de qualidade)

- **Jun/26**: Ed.1 (jul/26) publicou 530; Ed.2 (ago/26) corrigiu para 532 (revisão de base ANP).
- **Crescimento a.a. mar–jun/26**: mudaram entre edições (ex.: mar +51,5% → +62,1%) — a base
  2025 foi revisada retroativamente pela ANP. Usamos os valores da Ed.2 (mais recente).
- **Base 2025**: a.a. oficial do IEPUC (ago +53,7%) implica ago/25 = 344; a série bruta da
  ANP dá 386,1 (+37,0%). Mantemos o KPI oficial do boletim e publicamos a série ANP real
  como tendência histórica independente.

## Cobertura da 4WaTT nos dados públicos

- Nenhuma empresa 4WaTT/SPE associada aparece nas 21 usinas de biometano autorizadas pela ANP
  (varredura por razão social e município: BURITIS, FRANCA, GOIANIA, PALMEIRAS).
- Esperado: a ANP regula **biometano**; o core da 4WaTT é **biogás/biodigestão** (fora do
  escopo de regulação ANP). UTB Franca não consta como SPE no dataset.
- → Camada "micro" continua qualitativa (cases públicos); números internos exigem acesso à empresa.

## Artefatos derivados (gerados por `dados/preparar_anp.py`)

- `anp_abertos/anp_nacional_mensal_mm3d.csv` — série nacional mensal jan/2020–ago/2026 (Mm³/d),
  reconstruída do CSV estadual da ANP com as regras de parse acima.
- `../../limpos/producao_por_uf_anp_mensal.csv` — produção mensal por UF e região (mil m³/d).
- `../../limpos/producao_nacional_anp_historico.csv` — soma nacional mensal (mil m³/d).
- `../../limpos/usinas_anp_2026_08.csv` — 21 usinas autorizadas em ago/26, com município, capacidade
  e uso da capacidade de processamento de biogás.
