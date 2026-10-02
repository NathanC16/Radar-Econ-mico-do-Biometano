"""Baixa os rebanhos por UF do IBGE e estima o potencial de biogás da pecuária.

Execução (raiz do projeto):  .venv/bin/python dados/preparar_ibge.py [ano]

Fonte: IBGE — Pesquisa da Pecuária Municipal (PPM), via API SIDRA
  - Tabela 3939: efetivo dos rebanhos por tipo (galináceos e suínos)
  - Tabela 94:   vacas ordenhadas
Saídas:
  - dados/brutos/ibge/ppm_<ano>.json             resposta bruta da API (para auditoria)
  - dados/limpos/potencial_pecuaria_uf_ibge.csv  rebanhos e potencial de biogás por UF

Método: o mesmo do "Panorama do Biometano em Goiás" (Governo de Goiás/CBIE, 2026, seção 6.3.3),
com os coeficientes de produção de biogás por animal citados no estudo (EMBRAPA):
  aves 0,0014 · suínos 0,240 · vacas ordenhadas 0,360 m³ de biogás por cabeça por dia.
Aplicado aos dados de 2023, reproduz o potencial de Goiás do estudo com erro < 1%
(398,0 × 402,0 milhões m³/ano) — conferido em notebook/validar_dados.py.
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ANO = sys.argv[1] if len(sys.argv) > 1 else "2025"
COEF = {"aves": 0.0014, "suinos": 0.240, "vacas": 0.360}   # m³ biogás / cabeça / dia
URL = "https://apisidra.ibge.gov.br/values"
REGIAO = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
SIGLA = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
         "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
         "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
         "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


def sidra(caminho: str) -> list[dict]:
    with urllib.request.urlopen(f"{URL}/{caminho}?formato=json", timeout=60) as r:
        return json.load(r)


# classificação 79 da tabela 3939: 32794 = "Suíno - total" · 32796 = "Galináceos - total"
TIPOS = {"Suíno - total": "suinos", "Galináceos - total": "aves"}
rebanhos = sidra(f"t/3939/n3/all/v/105/p/{ANO}/c79/32794,32796")
vacas = sidra(f"t/94/n3/all/v/107/p/{ANO}")
(RAIZ / "brutos" / "ibge").mkdir(parents=True, exist_ok=True)
(RAIZ / "brutos" / "ibge" / f"ppm_{ANO}.json").write_text(
    json.dumps({"tabela_3939": rebanhos, "tabela_94": vacas}, ensure_ascii=False, indent=1),
    encoding="utf-8")

uf: dict[str, dict] = {}
for r in rebanhos[1:]:
    d = uf.setdefault(r["D1C"], {"estado": r["D1N"]})
    d[TIPOS[r["D4N"]]] = int(r["V"]) if r["V"].isdigit() else 0   # KeyError = tipo inesperado
for r in vacas[1:]:
    uf.setdefault(r["D1C"], {"estado": r["D1N"]})["vacas"] = int(r["V"]) if r["V"].isdigit() else 0

with open(RAIZ / "limpos" / "potencial_pecuaria_uf_ibge.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ano", "uf", "estado", "regiao", "aves", "suinos", "vacas_ordenhadas",
                "biogas_aves_m3_ano", "biogas_suinos_m3_ano", "biogas_vacas_m3_ano", "biogas_total_m3_ano"])
    for cod in sorted(uf, key=lambda c: SIGLA[c]):
        d = uf[cod]
        b = {k: round(d.get(k, 0) * COEF[k] * 365) for k in COEF}
        w.writerow([ANO, SIGLA[cod], d["estado"], REGIAO[cod[0]], d.get("aves", 0), d.get("suinos", 0),
                    d.get("vacas", 0), b["aves"], b["suinos"], b["vacas"], sum(b.values())])
print(f"PPM {ANO}: {len(uf)} UFs → dados/limpos/potencial_pecuaria_uf_ibge.csv")
