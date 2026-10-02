"""Gera as bases limpas da ANP a partir dos dados abertos brutos.

Execução (raiz do projeto):  .venv/bin/python dados/preparar_anp.py

Entradas  (dados/brutos/anp_abertos/, extraídas de biometano-dados-abertos.zip):
  - Biometano_DadosAbertos_CSV_Producao.csv    produção mensal por UF (m³ no mês)
  - Biometano_DadosAbertos_CSV_Capacidade.csv  capacidade e biogás processado por usina (m³/d)
Saídas (dados/limpos/):
  - producao_por_uf_anp_mensal.csv       produção mensal por UF e região (mil m³/d), 2020–2026
  - producao_nacional_anp_historico.csv  soma nacional mensal (mil m³/d)
  - usinas_anp_2026_08.csv               as usinas autorizadas em ago/2026, com UF e município
e atualiza dados/brutos/anp_abertos/anp_nacional_mensal_mm3d.csv (mesma série nacional).

Regras de leitura (conferidas contra o boletim IEPUC, ver PROVENIENCIA.md):
  - "Produção (m³)" é o volume do MÊS em m³ → divide-se pelos dias reais do mês
    (29 em fevereiro de ano bissexto) e por 1.000 para obter mil m³/d;
  - o número usa ponto como separador decimal ("4324235.558"); poucos valores pequenos
    ("173.037") ficam ambíguos — lidos como decimal, o que fecha o total nacional;
  - somam-se os produtos BIOMETANO e BIOMETANO COMPRIMIDO (SP e PR declaram parte da
    produção como comprimido); só assim a soma bate com o boletim (|Δ| < 0,5 mil m³/d);
  - na capacidade, "m³/d" está correto e usa vírgula decimal ("204000,00").
"""
import calendar
import csv
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BRUTOS = RAIZ / "brutos" / "anp_abertos"
LIMPOS = RAIZ / "limpos"

UF = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA",
    "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO",
}
REGIAO = {"NORTE": "Norte", "NORDESTE": "Nordeste", "CENTRO OESTE": "Centro-Oeste",
          "CENTRO-OESTE": "Centro-Oeste", "SUDESTE": "Sudeste", "SUL": "Sul"}


# a ANP grafa municípios em maiúsculas e sem acento
MUNICIPIO = {
    "PAULINIA": "Paulínia", "SEROPEDICA": "Seropédica", "JABOATAO DOS GUARARAPES": "Jaboatão dos Guararapes",
    "AMERICO BRASILIENSE": "Américo Brasiliense", "MINAS DO LEAO": "Minas do Leão",
    "PARAGUACU PAULISTA": "Paraguaçu Paulista", "SAO PAULO": "São Paulo", "SAO LEOPOLDO": "São Leopoldo",
    "SAO PEDRO DA ALDEIA": "São Pedro da Aldeia", "TUPACIGUARA": "Tupaciguara",
}
SIGLAS = {"GNR", "SPE", "ZEG", "CRI", "PPT", "S.A.", "S.A", "LTDA", "LTDA.", "SCBIO"}  # siglas mantidas
MINUSCULAS = {"DE", "DA", "DO", "DOS", "DAS", "E"}


def nome_proprio(txt: str) -> str:
    """'GNR FORTALEZA VALORIZAÇÃO DE BIOGÁS LTDA.' → 'GNR Fortaleza Valorização de Biogás Ltda.'"""
    txt = txt.replace("GESTÃODE", "GESTÃO DE")   # erro de digitação no cadastro da ANP
    out = []
    for i, w in enumerate(txt.split()):
        if w in SIGLAS and w not in ("LTDA", "LTDA."):
            out.append(w)
        elif w in MINUSCULAS and i > 0:
            out.append(w.lower())
        else:
            out.append("-".join(parte.capitalize() for parte in w.split("-")))
    return " ".join(out)


def ler(nome: str) -> list[dict]:
    with open(BRUTOS / nome, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def periodo(mes_ano: str) -> tuple[str, int]:
    """'08/2026' → ('2026-08', dias do mês)."""
    m, a = map(int, mes_ano.split("/"))
    return f"{a}-{m:02d}", calendar.monthrange(a, m)[1]


def num_br(txt: str) -> float:
    """'204000,00' → 204000.0 (vírgula decimal, sem milhar)."""
    return float(txt.replace(".", "").replace(",", ".")) if txt.strip() else 0.0


# ------------------------------------------------------------------ produção por UF
por_uf: dict[tuple, float] = defaultdict(float)
for r in ler("Biometano_DadosAbertos_CSV_Producao.csv"):
    per, dias = periodo(r["Mês/Ano"])
    chave = (per, REGIAO[r["Região"].strip().upper()], UF[r["Estado"].strip()], r["Estado"].strip())
    por_uf[chave] += float(r["Produção (m³)"]) / dias / 1000

linhas_uf = sorted(por_uf.items())
with open(LIMPOS / "producao_por_uf_anp_mensal.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["periodo", "regiao", "uf", "estado", "producao_mm3d"])
    for (per, reg, uf, est), v in linhas_uf:
        w.writerow([per, reg, uf, est, round(v, 2)])

nacional: dict[str, float] = defaultdict(float)
for (per, *_), v in linhas_uf:
    nacional[per] += v
with open(LIMPOS / "producao_nacional_anp_historico.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["periodo", "producao_mm3d"])
    for per in sorted(nacional):
        w.writerow([per, round(nacional[per], 1)])
with open(BRUTOS / "anp_nacional_mensal_mm3d.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["mes", "producao_mm3d_anp"])
    for per in sorted(nacional, key=lambda p: (p[5:], p[:4])):
        w.writerow([f"{per[5:]}/{per[:4]}", round(nacional[per], 1)])

# ------------------------------------------------------------------ usinas (ago/2026)
cap = [r for r in ler("Biometano_DadosAbertos_CSV_Capacidade.csv") if r["Mês/Ano"] == "08/2026"]
col_proc = next(c for c in cap[0] if c.startswith("Volume Processado/Capacidade"))
with open(LIMPOS / "usinas_anp_2026_08.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["usina", "regiao", "uf", "estado", "municipio", "capacidade_autorizada_mm3d",
                "capacidade_biogas_mm3d", "biogas_processado_mm3d", "uso_capacidade_biogas_pct"])
    for r in sorted(cap, key=lambda r: -num_br(r["Capacidade Autorizada de Produção de Biometano (m³/d)"])):
        w.writerow([
            nome_proprio(r["Razão Social"].strip()), REGIAO[r["Região"].strip().upper()],
            UF[r["Estado"].strip()], r["Estado"].strip(),
            MUNICIPIO.get(r["Município"].strip(), nome_proprio(r["Município"].strip())),
            round(num_br(r["Capacidade Autorizada de Produção de Biometano (m³/d)"]) / 1000, 2),
            round(num_br(r["Capacidade Processamento de Biogás(m³/d)"]) / 1000, 2),
            round(num_br(r["Volume Processado de Biogás (m³/d)"]) / 1000, 2),
            num_br(r[col_proc]),
        ])

print(f"UF×mês: {len(linhas_uf)} linhas · meses: {len(nacional)} · usinas ago/26: {len(cap)}")
print(f"ago/26 nacional = {nacional['2026-08']:.1f} mil m³/d · "
      f"capacidade ago/26 = {sum(num_br(r['Capacidade Autorizada de Produção de Biometano (m³/d)']) for r in cap) / 1000:.1f} mil m³/d")
