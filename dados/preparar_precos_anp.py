"""Preços de revenda dos combustíveis concorrentes do biometano, por UF (ANP).

Execução (raiz do projeto):  .venv/bin/python dados/preparar_precos_anp.py

Fonte: ANP — Levantamento de Preços de Combustíveis, série histórica mensal por estado
  https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/mensal/mensal-estados-desde-jan2013.xlsx
Entrada:  dados/brutos/anp_precos/mensal-estados-desde-jan2013.xlsx (baixada se não existir)
Saída:    dados/limpos/precos_combustiveis_uf_mensal.csv  (jan/2020 em diante)

Produtos mantidos: óleo diesel S10 (R$/l) e GNV (R$/m³) — os substitutos diretos do biometano
em frota e indústria. Para comparar na mesma base, o diesel é convertido em R$ por m³ de
biometano equivalente com o fator citado no "Panorama do Biometano em Goiás" (CIBiogás):
1 m³ de biometano ≈ 0,87 l de diesel. O GNV já é cotado em R$/m³ (energia equivalente).
"""
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
URL = ("https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/"
       "precos-revenda-e-de-distribuicao-combustiveis/shlp/mensal/mensal-estados-desde-jan2013.xlsx")
BRUTO = RAIZ / "brutos" / "anp_precos" / "mensal-estados-desde-jan2013.xlsx"
DIESEL_POR_M3 = 0.87   # l de diesel substituídos por 1 m³ de biometano (CIBiogás)
SIGLA = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM", "BAHIA": "BA", "CEARA": "CE",
    "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES", "GOIAS": "GO", "MARANHAO": "MA",
    "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG", "PARA": "PA",
    "PARAIBA": "PB", "PARANA": "PR", "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO", "RORAIMA": "RR",
    "SANTA CATARINA": "SC", "SAO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO",
}
REGIAO = {"NORTE": "Norte", "NORDESTE": "Nordeste", "CENTRO OESTE": "Centro-Oeste",
          "SUDESTE": "Sudeste", "SUL": "Sul"}
PRODUTOS = {"OLEO DIESEL S10": "Diesel S10", "GNV": "GNV"}

if not BRUTO.exists():
    BRUTO.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, BRUTO)

x = pd.read_excel(BRUTO, header=16)   # 16 linhas de cabeçalho/notas da ANP antes da tabela
x = x[x["PRODUTO"].isin(PRODUTOS) & (x["MÊS"] >= "2020-01-01")].copy()
saida = pd.DataFrame({
    "periodo": pd.to_datetime(x["MÊS"]).dt.strftime("%Y-%m"),
    "uf": x["ESTADO"].map(SIGLA),
    "regiao": x["REGIÃO"].str.strip().map(REGIAO),
    "produto": x["PRODUTO"].map(PRODUTOS),
    "unidade": x["UNIDADE DE MEDIDA"],
    "preco_revenda": x["PREÇO MÉDIO REVENDA"].round(3),
    "postos_pesquisados": x["NÚMERO DE POSTOS PESQUISADOS"],
})
assert saida[["uf", "regiao", "produto"]].notna().all().all(), "UF/região/produto não mapeado"
# R$ por m³ de biometano equivalente (base comum de comparação)
saida["preco_m3_biometano_eq"] = saida["preco_revenda"].where(
    saida["produto"] == "GNV", (saida["preco_revenda"] * DIESEL_POR_M3)).round(3)
saida = saida.sort_values(["periodo", "uf", "produto"])
saida.to_csv(RAIZ / "limpos" / "precos_combustiveis_uf_mensal.csv", index=False)
ult = saida["periodo"].max()
print(f"{len(saida)} linhas · {saida['periodo'].min()} → {ult} · "
      f"UFs com GNV em {ult}: {saida[(saida.periodo == ult) & (saida.produto == 'GNV')].uf.nunique()}")
