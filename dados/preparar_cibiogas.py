"""Plantas de biogás por estado e números nacionais do setor (CIBiogás — BiogásMap).

Execução (raiz do projeto):  .venv/bin/python dados/preparar_cibiogas.py

Fontes (CIBiogás — Centro Internacional de Energias Renováveis, levantamento BiogásMap):
- Panorama do Biogás no Brasil 2023 (Relatório Técnico nº 001/2024), licença CC BY 4.0:
  https://abiogas.com.br/wp-content/uploads/protectedfiles/Panorama%20do%20Biog%C3%A1s%202023%20-%20CIbiog%C3%A1s%20(2024).pdf
  Entrada: dados/brutos/cibiogas/panorama_biogas_brasil_2023.txt (texto extraído com
  `pdftotext -layout`; o PDF é baixado e extraído se o .txt não existir).
- Panoramas 2024 e 2025: o e-book só é entregue após cadastro no site da CIBiogás. Os números
  usados vêm das notícias da ABEGÁS sobre cada edição, guardadas como trechos citados em
  dados/brutos/cibiogas/abegas_panorama_biogas_2024.txt e ..._2025.txt (URL e data no topo).

Saídas (dados/limpos/):
- plantas_biogas_uf_cibiogas.csv — plantas de biogás por estado: os 10 maiores em 2022 e 2023
  (gráfico da pág. 9 do Panorama 2023) e os 5 maiores em 2025; produção de biogás 2025 dos 4
  maiores produtores.
- biogas_brasil_cibiogas.csv — totais nacionais por edição (plantas de biogás e de biometano,
  produção e destino do biogás).

Cada edição revisa os anos anteriores (plantas antigas entram no cadastro depois), por isso um
mesmo ano pode ter números diferentes em edições diferentes; aqui cada valor fica com a sua edição.
"""
import re
import subprocess
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
BRUTOS = RAIZ / "brutos" / "cibiogas"
URL_2023 = ("https://abiogas.com.br/wp-content/uploads/protectedfiles/"
            "Panorama%20do%20Biog%C3%A1s%202023%20-%20CIbiog%C3%A1s%20(2024).pdf")
PDF_2023 = BRUTOS / "panorama_biogas_brasil_2023.pdf"
TXT_2023 = BRUTOS / "panorama_biogas_brasil_2023.txt"
# ordem das barras no gráfico "Número de plantas nos 10 estados mais representativos" (pág. 9);
# a camada de texto do PDF traz os números na mesma ordem, sem as siglas
ORDEM_2023 = ["PR", "MG", "SC", "SP", "GO", "MS", "RS", "MT", "RJ", "PE"]
NOME = {"PR": "Paraná", "MG": "Minas Gerais", "SC": "Santa Catarina", "SP": "São Paulo",
        "GO": "Goiás", "MS": "Mato Grosso do Sul", "RS": "Rio Grande do Sul",
        "MT": "Mato Grosso", "RJ": "Rio de Janeiro", "PE": "Pernambuco"}


def num(txt: str) -> float:
    return float(txt.replace(".", "").replace(",", "."))


if not TXT_2023.exists():
    if not PDF_2023.exists():
        BRUTOS.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL_2023, PDF_2023)
    subprocess.run(["pdftotext", "-layout", str(PDF_2023), str(TXT_2023)], check=True)

t23 = TXT_2023.read_text(encoding="utf-8")
t24 = " ".join((BRUTOS / "abegas_panorama_biogas_2024.txt").read_text(encoding="utf-8").split())
t25 = " ".join((BRUTOS / "abegas_panorama_biogas_2025.txt").read_text(encoding="utf-8").split())

# ------------------------------------------------------------ por estado
bloco = t23.split("Número de plantas nos 10 estados mais representativos")[1].split("Até 2022")[0]
barras = re.findall(r"^\s*(\d+)\s+(\d+)\s+(\d+)%\s*$", bloco, flags=re.M)
assert len(barras) == len(ORDEM_2023), f"esperadas 10 barras, lidas {len(barras)}"
linhas = []
for uf, (ate22, novas, cresc) in zip(ORDEM_2023, barras):
    ate22, novas, cresc = int(ate22), int(novas), int(cresc)
    assert round(novas / ate22 * 100) == cresc, f"{uf}: crescimento não confere"
    ed = "Panorama do Biogás 2023"
    linhas += [dict(ano=2022, uf=uf, plantas_biogas=ate22, edicao=ed),
               dict(ano=2023, uf=uf, plantas_biogas=ate22 + novas, edicao=ed)]

m = re.search(r"Paraná aparece na primeira colocação do ranking, com (\d+) usinas, seguido de Minas "
              r"Gerais, com (\d+), Santa Catarina \((\d+)\), São Paulo \((\d+)\) e Goiás \((\d+)\)", t25)
for uf, v in zip(["PR", "MG", "SC", "SP", "GO"], m.groups()):
    linhas.append(dict(ano=2025, uf=uf, plantas_biogas=int(v), edicao="Panorama do Biogás 2025"))

m = re.search(r"São Paulo lidera o ranking dos Estados produtores, com ([\d,]+) milhões de m3/dia, seguido "
              r"por Rio de Janeiro, com ([\d,]+) milhão de m3/dia, Paraná \(([\d,]+) milhão de m3/dia\) e "
              r"Minas Gerais \(([\d,]+) milhão de m3/dia\)", t25)
prod25 = {uf: num(v) * 1000 for uf, v in zip(["SP", "RJ", "PR", "MG"], m.groups())}   # mil m³/d

uf_df = pd.DataFrame(linhas)
uf_df = uf_df.merge(pd.DataFrame([dict(ano=2025, uf=u, producao_biogas_mil_m3d=v) for u, v in prod25.items()]),
                    on=["ano", "uf"], how="outer")
uf_df["edicao"] = uf_df["edicao"].fillna("Panorama do Biogás 2025")
uf_df["estado"] = uf_df["uf"].map(NOME)
uf_df["plantas_biogas"] = uf_df["plantas_biogas"].astype("Int64")
uf_df = uf_df[["ano", "uf", "estado", "plantas_biogas", "producao_biogas_mil_m3d", "edicao"]]
uf_df = uf_df.sort_values(["ano", "plantas_biogas"], ascending=[True, False])
uf_df.to_csv(RAIZ / "limpos" / "plantas_biogas_uf_cibiogas.csv", index=False)

# ------------------------------------------------------------ Brasil
geral = t23.split("Visão Geral do Biogás")[-1]          # [-1]: a 1ª ocorrência é o sumário
m = re.search(r"(\d\.\s?\d{3})\s+(\d+)\s+[\d,]+ bi", geral)
plantas23, novas23 = int(m.group(1).replace(".", "").replace(" ", "")), int(m.group(2))
bm = t23.split("Visão Geral do Biometano")[-1]
m = re.search(r"^\s*(\d+)\s{20,}(\d+)\s*$", bm, flags=re.M)   # "50 ... 4" (plantas · em instalação)
biomet23 = int(m.group(1))

br = [
    (2023, "plantas_biogas", plantas23, "plantas", "Panorama do Biogás 2023"),
    (2023, "novas_plantas_biogas", novas23, "plantas", "Panorama do Biogás 2023"),
    (2023, "plantas_biometano", biomet23, "plantas", "Panorama do Biogás 2023"),
]
m = re.search(r"totalizou (\d+) plantas de biogás cadastradas no ano passado, sendo (\d+) unidades em "
              r"operação e (\d+) em fase de implementação", t24)
br += [(2024, "plantas_biogas", int(m.group(1)), "plantas", "Panorama do Biogás 2024"),
       (2024, "plantas_biogas_operacao", int(m.group(2)), "plantas", "Panorama do Biogás 2024")]
m = re.search(r"registrou (\d+) plantas de biometano cadastradas no ano passado, sendo (\d+) unidades "
              r"operacionais", t24)
br += [(2024, "plantas_biometano", int(m.group(1)), "plantas", "Panorama do Biogás 2024"),
       (2024, "plantas_biometano_operacao", int(m.group(2)), "plantas", "Panorama do Biogás 2024")]
m = re.search(r"totalizou ([\d.]+) usinas de biogás cadastradas, com produção acumulada próxima de "
              r"(\d+) bilhões de m³, em 2025, ou ([\d,]+) milhões de m³ por dia", t25)
br += [(2025, "plantas_biogas", int(num(m.group(1))), "plantas", "Panorama do Biogás 2025"),
       (2025, "producao_biogas", num(m.group(3)) * 1000, "mil m³/d", "Panorama do Biogás 2025")]
m = re.search(r"(\d+)% do biogás é destinado para a geração de energia elétrica, enquanto (\d+)% vão "
              r"para a produção do biometano", t25)
br += [(2025, "pct_biogas_energia_eletrica", int(m.group(1)), "%", "Panorama do Biogás 2025"),
       (2025, "pct_biogas_biometano", int(m.group(2)), "%", "Panorama do Biogás 2025")]
m = re.search(r"volume de biometano produzido foi de ([\d,]+) milhão de m3/dia", t25)
br.append((2025, "producao_biometano", num(m.group(1)) * 1000, "mil m³/d", "Panorama do Biogás 2025"))

br_df = pd.DataFrame(br, columns=["ano", "indicador", "valor", "unidade", "edicao"])
br_df.to_csv(RAIZ / "limpos" / "biogas_brasil_cibiogas.csv", index=False)

print(f"{len(uf_df)} linhas por estado · {len(br_df)} indicadores nacionais · "
      f"GO: {uf_df[uf_df.uf == 'GO'][['ano', 'plantas_biogas']].values.tolist()}")
