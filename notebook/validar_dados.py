"""Validação programática das bases limpos/ contra o boletim IEPUC (ago/2026).

Execução:  .venv/bin/python notebook/validar_dados.py
Todo número publicado no dashboard foi transcrito das fontes e checado aqui:
(1) contra valores publicados (constantes) e consistência interna; (2) contra o
texto extraído dos PDFs em dados/brutos/ (busca literal dos valores).
Saidas: tabela PASS/FAIL por verificação; exit code != 0 se houver falha.
"""
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent / "dados" / "limpos"
pm = pd.read_csv(BASE / "producao_mensal_2026.csv")
pe = pd.read_csv(BASE / "producao_por_estado_2026_08.csv")
mp = pd.read_csv(BASE / "producao_por_materia_prima_2026_08.csv")
pu = pd.read_csv(BASE / "producao_por_usina_2026_08.csv")
cap = pd.read_csv(BASE / "capacidade_anp.csv")
_com = pd.read_csv(BASE / "comercializacao.csv")
com = dict(zip(_com["indicador"], _com["valor"]))

# Valores publicados no boletim (transcritos da camada de texto do PDF)
AGOSTO_NACIONAL = 529                      # "a produção ... atingiu 529 Mm³/d"
MENSAL_2026 = [384, 410, 404, 451, 451, 532, 561, 529]
MEDIA_ACUMULADA = [384, 396, 399, 412, 420, 439, 456, 466]
CRES_AA = [57.68, 67.06, 62.11, 61.27, 56.97, 58.02, 56.99, 53.74]   # % vs mês igual de 2025
VAR_MENSAL = [-0.57, 6.90, -1.54, 11.64, 0.12, 17.77, 5.47, -5.64]
ESTADOS = {"RJ": (139, 2), "SP": (178, 9), "CE": (37, 1), "RS": (86, 3),
           "PE": (84, 1), "OUTROS": (5, 5)}          # (produção Mm³/d, nº usinas)
PCT_NARRATIVA = {"SP": 33.6, "RJ": 26.4, "RS": 16.2, "PE": 16.0, "CE": 6.9}
MAT_PRIMA = {"Aterro sanitário": (425, 10), "Sucroenergético": (99, 7), "Outros resíduos": (5, 4)}
USINA_GAS_VERDE = 139.48
CAP_ROWS = [("2025-06", 697, 1510, 2207, 12, 38),
            ("2026-07", 1368, 2009, 3378, 21, 49),
            ("2026-08", 1368, 2023, 3391, 21, 49)]

results = []


def check(nome: str, ok: bool, detalhe: str = "") -> None:
    results.append((nome, ok, detalhe))


# ---------------------------------------------------------------- mensal
check("mensal: produção 2026 coincide com o boletim",
      pm["producao_mm3d"].tolist() == MENSAL_2026, f'{pm["producao_mm3d"].tolist()}')
check("mensal: agosto/2026 == 529 Mm³/d (manchete do boletim)",
      int(pm.loc[pm.mes == "Ago", "producao_mm3d"].iloc[0]) == AGOSTO_NACIONAL)
check("mensal: média acumulada coincide com o boletim",
      pm["media_acumulada_2026_mm3d"].tolist() == MEDIA_ACUMULADA)
check("mensal: crescimento vs ano anterior coincide com o boletim",
      pm["crescimento_vs_ano_anterior_pct"].tolist() == CRES_AA, f'{pm["crescimento_vs_ano_anterior_pct"].tolist()}')

# verificação cruzada: variação mensal recalculada a partir dos valores publicados
recom = (pm["producao_mm3d"] / pm["producao_mm3d"].shift(1) - 1) * 100
dif = (recom.iloc[1:].round(2) - pd.Series(VAR_MENSAL)[1:]).abs()
check("mensal: variação mensal recalculada ≈ publicada (tol. 0,4 pp p/ arredondamento)",
      bool(dif.max() <= 0.4), f'máx |diff| = {dif.max():.2f} pp')

# série 2025 derivada do crescimento a.a. publicado + coerência
pm25 = (pm["producao_mm3d"] / (1 + pm["crescimento_vs_ano_anterior_pct"] / 100)).round(1)
check("mensal: série 2025 derivada dentro de faixa plausível (150–400 Mm³/d)",
      bool(((pm25 >= 150) & (pm25 <= 400)).all()), f'2025 derivada = {pm25.tolist()}')
cres_media = pm["producao_mm3d"].mean() / pm25.mean() - 1
check("mensal: média jan–ago/26 ≈ +59% sobre jan–ago/25 DERIVADA (só auditoria; o painel usa a ANP)",
      abs(cres_media - 0.59) < 0.02, f'2025 media={pm25.mean():.0f} → +{cres_media*100:.1f}%')

# ---------------------------------------------------------------- estado
pe_pub = {r.uf: (int(r.producao_mm3d), int(r.num_usinas)) for r in pe.itertuples()}
check("estado: produção/nº de usinas por UF coincidem com o boletim",
      pe_pub == ESTADOS, f'{pe_pub}')
soma_est = int(pe["producao_mm3d"].sum())
soma_us = int(pe["num_usinas"].sum())
check("estado: SOMA das UFs == 529 (total nacional publicado)", soma_est == AGOSTO_NACIONAL, f"soma={soma_est}")
check("estado: SOMA de usinas == 21 (usinas autorizadas pela ANP)", soma_us == 21, f"soma={soma_us}")

pe5 = pe[pe.uf != "OUTROS"].set_index("uf")
pct_calc = (pe5["producao_mm3d"] / AGOSTO_NACIONAL * 100).round(1)
dif_pct = pd.Series({u: abs(pct_calc[u] - PCT_NARRATIVA[u]) for u in PCT_NARRATIVA})
check("estado: participações % recalculadas ≈ texto do boletim (tol. 0,2 pp)",
      bool(dif_pct.max() <= 0.2), f'calculado={pct_calc.to_dict()} | máx|diff|={dif_pct.max():.2f} pp')

top5 = pe[pe.uf != "OUTROS"]["producao_mm3d"].sum()
check("estado: top 5 UFs ≈ 99% da produção", abs(top5 / AGOSTO_NACIONAL - 0.99) < 0.01,
      f'top5={top5} → {top5/AGOSTO_NACIONAL*100:.1f}%')

# verificação cruzada usina→estado (inferência validada pelos números)
gvr = float(pu.loc[pu.usina == "GNR Fortaleza", "producao_mm3d"].iloc[0])
orz = float(pu.loc[pu.usina.str.startswith("Orizon"), "producao_mm3d"].iloc[0])
gasv = float(pu.loc[pu.usina == "Gás Verde", "producao_mm3d"].iloc[0])
check("cruzado: GNR Fortaleza (CE) ≈ produção CE do boletim (37)", abs(gvr - 37) <= 0.5, f"{gvr}")
check("cruzado: Orizon Jaboatão (PE) ≈ produção PE do boletim (84)", abs(orz - 84) <= 1, f"{orz}")
check("cruzado: Gás Verde (RJ, frota Seropédica no boletim) ≈ produção RJ (139)", abs(gasv - 139) <= 1, f"{gasv}")

# ---------------------------------------------------------------- usina
soma_usinas = round(float(pu["producao_mm3d"].sum()), 1)
check("usina: soma da tabela ≈ 529 (tol. 1 p/ arredondamento)", abs(soma_usinas - AGOSTO_NACIONAL) <= 1, f"soma={soma_usinas}")
leader = pu.loc[pu["producao_mm3d"].idxmax()]
check("usina: líder = Gás Verde, com ~26% da produção nacional",
      leader.usina == "Gás Verde" and abs(float(leader.producao_mm3d) / AGOSTO_NACIONAL - 0.264) < 0.01,
      f'{leader.usina} = {leader.producao_mm3d} ({float(leader.producao_mm3d)/AGOSTO_NACIONAL*100:.1f}%)')

# ---------------------------------------------------------------- matéria-prima
mp_pub = {r.materia_prima: (int(r.producao_mm3d), int(r.num_usinas)) for r in mp.itertuples()}
check("matéria-prima: produção/usinas coincidem com o boletim", mp_pub == MAT_PRIMA, f"{mp_pub}")
check("matéria-prima: soma == 529 e usinas == 21",
      int(mp["producao_mm3d"].sum()) == AGOSTO_NACIONAL and int(mp["num_usinas"].sum()) == 21)
aterro_pct = 425 / AGOSTO_NACIONAL * 100
check("matéria-prima: aterros ≈ 80,3% (texto do boletim)", abs(aterro_pct - 80.3) < 0.1, f"{aterro_pct:.1f}%")

# ---------------------------------------------------------------- capacidade
for periodo, aut, sol, tot, conc, ped in CAP_ROWS:
    row = cap[cap.periodo == periodo].iloc[0]
    ok = (int(row.autorizada_mm3d), int(row.solicitada_mm3d), int(row.total_mm3d),
          int(row.usinas_concedidas), int(row.pedidos_em_tramitacao)) == (aut, sol, tot, conc, ped)
    check(f"capacidade {periodo}: valores == boletim", ok,
          f'({int(row.autorizada_mm3d)}, {int(row.solicitada_mm3d)}, {int(row.total_mm3d)}, {int(row.usinas_concedidas)}, {int(row.pedidos_em_tramitacao)})')
    # tolerância de 2 Mm³/d: o boletim publica valores arredondados
    # (ex.: jul/26 → 1368+2009=3377 vs total publicado 3.378)
    check(f"capacidade {periodo}: total ≈ autorizada + solicitada (tol. 2, arredondamento da fonte)",
          abs(int(row.autorizada_mm3d) + int(row.solicitada_mm3d) - int(row.total_mm3d)) <= 2)
    total_usinas_esperado = 50 if periodo == "2025-06" else 70
    check(f"capacidade {periodo}: concedidas + pedidos == total de usinas ({total_usinas_esperado})",
          int(row.usinas_concedidas) + int(row.pedidos_em_tramitacao) == total_usinas_esperado)

cres_aut = (1368 / 697 - 1) * 100
check("capacidade: autorizada cresceu ~+96% de jun/25 → ago/26 ('dobrou em um ano')",
      abs(cres_aut - 96.3) < 0.5, f"+{cres_aut:.1f}%")

# ---------------------------------------------------------------- comercialização
check("comercialização: GNC + gasoduto == 55 transações",
      int(com["Entregas por GNC (veículo)"]) + int(com["Entregas por gasoduto de distribuição"]) == 55)
# O texto do boletim publica: 38 registrados; em jul/26, 30 vigentes e 6 expirados.
# (os 2 restantes figuram com outro status no registro da ANP — fidelidade ao publicado)
check("comercialização: 30 vigentes e 6 expirados conforme texto do boletim",
      int(com["Contratos vigentes (jul/2026)"]) == 30 and int(com["Contratos expirados"]) == 6)

# ---------------------------------------------------------------- validação cruzada ANP × IEPUC
# Dados abertos da ANP (dados/brutos/anp_abertos) — série nacional reconstruída
# somando os estados; âncoras: totais publicados no boletim IEPUC.
_brutos = Path(__file__).resolve().parent.parent / "dados" / "brutos"
anp_ser = pd.read_csv(_brutos / "anp_abertos" / "anp_nacional_mensal_mm3d.csv", dtype={"mes": str})
anp_map = dict(zip(anp_ser["mes"], anp_ser["producao_mm3d_anp"]))
for i, iepuc_val in enumerate(MENSAL_2026, start=1):
    mes = f"{i:02d}/2026"
    anp_val = anp_map.get(mes)
    check(f"ANP×IEPUC {mes}: |Δ| ≤ 1,0 mil m³/d (validação cruzada de fontes)",
          anp_val is not None and abs(anp_val - iepuc_val) <= 1.0,
          f"ANP={anp_val} IEPUC={iepuc_val}")

hist = pd.read_csv(BASE / "producao_nacional_anp_historico.csv")
hist_map = {f"{p[5:]}/{p[:4]}": v for p, v in zip(hist["periodo"], hist["producao_mm3d"])}
check("ANP: série histórica limpa (2020–2026) == série reconstruída em dados/brutos",
      hist_map == anp_map and len(hist) == 80, f"{len(hist)} meses")
a25 = [hist_map[f"{m:02d}/2025"] for m in range(1, 9)]  # jan–ago/2025
check("ANP: série jan–ago/2025 completa e no intervalo plausível (200–450 mil m³/d)",
      len(a25) == 8 and all(200 <= v <= 450 for v in a25), f"{a25}")
cres_anp = 466 / (sum(a25) / 8) - 1
check("ANP: média jan–ago/26 (466, publicada) ≈ +54% sobre jan–ago/25 da ANP (texto do painel)",
      abs(cres_anp - 0.54) < 0.01, f"+{cres_anp*100:.1f}%")
aa_ago = 529 / a25[7] - 1
check("ANP: ago/26 ≈ +37% sobre ago/25 da ANP (IEPUC publica +53,74%: base 2025 diverge)",
      abs(aa_ago - 0.37) < 0.01, f"+{aa_ago*100:.1f}% (ago/25 ANP={a25[7]})")

# ---------------------------------------------------------------- dados regionais (ANP por UF e por usina)
# Gerados por dados/preparar_anp.py a partir dos CSVs brutos da ANP.
uf_mes = pd.read_csv(BASE / "producao_por_uf_anp_mensal.csv")
ago_uf = uf_mes[uf_mes.periodo == "2026-08"].set_index("uf")["producao_mm3d"]
for uf, (prod, _) in ESTADOS.items():
    if uf == "OUTROS":
        outros = float(ago_uf.drop(["RJ", "SP", "CE", "RS", "PE"], errors="ignore").sum())
        check("regional: 'Outros estados' do boletim (5) ≈ soma das demais UFs na ANP",
              abs(outros - prod) <= 1, f"ANP={outros:.2f} ({', '.join(ago_uf.drop(['RJ','SP','CE','RS','PE']).index)})")
    else:
        check(f"regional: {uf} ago/26 — ANP ≈ boletim ({prod}) |Δ| ≤ 1",
              abs(float(ago_uf.get(uf, 0)) - prod) <= 1, f"ANP={ago_uf.get(uf, 0)}")
soma_uf = uf_mes.groupby("periodo")["producao_mm3d"].sum().round(1)
hist_nac = pd.read_csv(BASE / "producao_nacional_anp_historico.csv").set_index("periodo")["producao_mm3d"]
check("regional: soma das UFs == série nacional em todos os 80 meses (tol. 0,1 de arredondamento)",
      bool((soma_uf - hist_nac).abs().max() <= 0.1 + 1e-9) and len(hist_nac) == 80)
check("regional: fevereiro de ano bissexto usa 29 dias (fev/2024 ≈ 225,3, não 233,3)",
      abs(hist_nac["2024-02"] - 225.3) <= 0.1, f"{hist_nac['2024-02']}")

us = pd.read_csv(BASE / "usinas_anp_2026_08.csv")
check("usinas ANP: 21 usinas autorizadas em ago/26 (== boletim)", len(us) == 21, f"{len(us)}")
check("usinas ANP: capacidade somada ≈ 1.368 mil m³/d (boletim) |Δ| ≤ 1",
      abs(us.capacidade_autorizada_mm3d.sum() - 1368) <= 1, f"{us.capacidade_autorizada_mm3d.sum():.1f}")
check("usinas ANP: 9 UFs com usina, nenhuma no Norte, 1 no Centro-Oeste (MS), nenhuma em GO",
      us.uf.nunique() == 9 and "Norte" not in set(us.regiao)
      and list(us[us.regiao == "Centro-Oeste"].uf) == ["MS"] and "GO" not in set(us.uf),
      f"UFs={sorted(us.uf.unique())}")
maior = us.loc[us.capacidade_autorizada_mm3d.idxmax()]
check("usinas ANP: maior capacidade = Paulínia/SP (~226) com uso de biogás < 1% (texto do painel)",
      maior.municipio == "Paulínia" and abs(maior.capacidade_autorizada_mm3d - 225.8) < 0.5
      and maior.uso_capacidade_biogas_pct < 1, f"{maior.usina} {maior.capacidade_autorizada_mm3d}")

# ---------------------------------------------------------------- IBGE (rebanhos) e ANP (preços)
pec = pd.read_csv(BASE / "potencial_pecuaria_uf_ibge.csv")
check("IBGE: 27 UFs e total = aves + suínos + vacas em cada UF",
      len(pec) == 27 and bool((pec.biogas_aves_m3_ano + pec.biogas_suinos_m3_ano
                               + pec.biogas_vacas_m3_ano == pec.biogas_total_m3_ano).all()))
check("IBGE: coeficientes do estudo de Goiás (aves 0,0014 · suínos 0,240 · vacas 0,360 m³/cab/dia)",
      bool((abs(pec.biogas_suinos_m3_ano - pec.suinos * 0.240 * 365) <= 1).all()
           and (abs(pec.biogas_vacas_m3_ano - pec.vacas_ordenhadas * 0.360 * 365) <= 1).all()
           and (abs(pec.biogas_aves_m3_ano - pec.aves * 0.0014 * 365) <= 1).all()))
_ppm23 = BASE.parent / "brutos" / "ibge" / "ppm_2023.json"
if _ppm23.exists():
    _j = json.loads(_ppm23.read_text(encoding="utf-8"))
    _go = {r["D4N"]: int(r["V"]) for r in _j["tabela_3939"][1:] if r["D1C"] == "52"}
    _vac = next(int(r["V"]) for r in _j["tabela_94"][1:] if r["D1C"] == "52")
    _pot = (_go["Galináceos - total"] * 0.0014 + _go["Suíno - total"] * 0.240 + _vac * 0.360) * 365
    check("IBGE: método aplicado ao IBGE 2023 reproduz Goiás do estudo (401.991.067 m³/ano) com erro < 1,5%",
          abs(_pot / 401991067 - 1) < 0.015, f"{_pot:,.0f} ({(_pot / 401991067 - 1) * 100:+.2f}%)")
go_pos = int(pec.biogas_total_m3_ano.rank(ascending=False)[pec.uf == "GO"].iloc[0])
go_vac = int(pec.biogas_vacas_m3_ano.rank(ascending=False)[pec.uf == "GO"].iloc[0])
check("IBGE: Goiás 5º em potencial total e 2º em vacas ordenhadas (texto do painel/relatório)",
      go_pos == 5 and go_vac == 2, f"total {go_pos}º · vacas {go_vac}º")

pr = pd.read_csv(BASE / "precos_combustiveis_uf_mensal.csv")
ult = pr[pr.periodo == pr.periodo.max()]
check("ANP preços: 27 UFs com diesel S10 no último mês; GO sem GNV",
      ult[ult.produto == "Diesel S10"].uf.nunique() == 27
      and "GO" not in set(ult[ult.produto == "GNV"].uf), f"último mês {pr.periodo.max()}")
_gnv_go = pr[(pr.uf == "GO") & (pr.produto == "GNV")]
check("ANP preços: GNV em GO = só 4 registros esporádicos, todos de 1 posto (texto do painel)",
      len(_gnv_go) == 4 and bool((_gnv_go.postos_pesquisados == 1).all()), f"{list(_gnv_go.periodo)}")
dsl = pr[pr.produto == "Diesel S10"]
check("ANP preços: diesel em R$/m³ de biometano eq. = preço × 0,87 (fator CIBiogás)",
      bool((abs(dsl.preco_m3_biometano_eq - dsl.preco_revenda * 0.87) < 0.001).all()))
_dgo = float(ult[(ult.uf == "GO") & (ult.produto == "Diesel S10")].preco_m3_biometano_eq.iloc[0])
check("ANP preços: diesel equivalente em GO acima do GNV de todos os estados (texto do painel)",
      _dgo > ult[ult.produto == "GNV"].preco_revenda.max(),
      f"GO diesel eq = {_dgo:.2f} · GNV máx = {ult[ult.produto == 'GNV'].preco_revenda.max():.2f}")

# ---------------------------------------------------------------- cadastro de fontes
import json
fontes = {k: v for k, v in json.loads((BASE.parent / "fontes.json").read_text(encoding="utf-8")).items()
          if not k.startswith("_")}
cadastrados = [a for f in fontes.values() for a in f["arquivos"]]
csvs = sorted(f.name for f in BASE.glob("*.csv"))
check("fontes.json: todo CSV de dados/limpos pertence a exatamente uma fonte cadastrada",
      sorted(cadastrados) == csvs, f"sem fonte: {sorted(set(csvs) - set(cadastrados))} · "
      f"inexistentes: {sorted(set(cadastrados) - set(csvs))}")

# ---------------------------------------------------------------- conferência contra o texto bruto
# Além das constantes acima, os valores das bases são procurados literalmente no
# texto extraído (pdftotext) das fontes em dados/brutos/ — evita que um erro de
# digitação seja repetido nos dois lados da comparação.
BRUTOS = BASE.parent / "brutos"
boletim = (BRUTOS / "iepuc_boletim_raw.txt").read_text(encoding="utf-8")
# o estudo de Goiás tem copyright e não é versionado (.gitignore); sem ele, as
# checagens literais do estudo são puladas (SKIP) em vez de falharem
_pan = BRUTOS / "panorama_biometano_goias_sgg_2026.txt"
panorama = _pan.read_text(encoding="utf-8") if _pan.exists() else None


def br(x: float, dec: int) -> str:
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


linhas_faltando = [
    f"{r.mes} {r.producao_mm3d} {br(r.variacao_vs_mes_anterior_pct, 2)}% "
    f"{r.media_acumulada_2026_mm3d} {br(r.crescimento_vs_ano_anterior_pct, 2)}%"
    for r in pm.itertuples()
]
linhas_faltando = [l for l in linhas_faltando if l not in boletim]
check("bruto: cada linha da tabela mensal aparece literalmente no boletim",
      not linhas_faltando, f"faltando: {linhas_faltando}")

ut = pd.read_csv(BASE / "utilizacao_capacidade_2026_08.csv")
for col, rot in [("taxa_utilizacao_pct", "Taxa de utilização"),
                 ("var_vs_mes_anterior_pct", "mês anterior"),
                 ("media_no_ano_pct", "média no ano"),
                 ("var_vs_ano_anterior_pct", "ano anterior")]:
    linha = rot + " " + " ".join(f"{br(v, 1)}%" for v in ut[col])
    check(f"bruto: utilização — linha '{rot}' aparece no boletim", linha in boletim, linha)
check("utilização: Brasil 38,7% é a taxa citada no texto do boletim",
      "utilização da capacidade autorizada de\nbiometano no Brasil foi de 38,7%" in boletim)

ren = dict(zip(pd.read_csv(BASE / "renovabio.csv")["indicador"],
               pd.read_csv(BASE / "renovabio.csv")["valor"]))
for chave, trecho in [
    ("Preço médio do CBio em ago/2026 (R$/tCO2eq)", "R$ 24,53"),
    ("Intensidade de carbono média das usinas certificadas (gCO2eq/MJ)", "9,36 gCO₂eq./MJ"),
    ("CBios emitidos por produtores de biometano em ago/2026 (mil)", "19,5 mil CBios"),
    ("CBios emitidos acumulados em 2026 (mil)", "128,3 mil CBios"),
]:
    check(f"bruto: RenovaBio '{trecho}' aparece no boletim e bate com a base",
          trecho in boletim and trecho.startswith(("R$ ", br(ren[chave], 2), br(ren[chave], 1))),
          f"base={ren[chave]}")

# Panorama do Biometano em Goiás (Governo de Goiás/CBIE)
gf = pd.read_csv(BASE / "potencial_biogas_goias.csv")
gm = pd.read_csv(BASE / "potencial_biogas_goias_municipios.csv")
total_go = int(gf["potencial_biogas_m3_ano"].sum())
check("goiás: soma das 3 fontes == total do estudo (2.725.238.404,69 m³/ano, tol. 1)",
      abs(total_go - 2725238404.69) <= 1, f"soma={total_go:,}")
if panorama is None:
    print("SKIP | checagens literais do Panorama de Goiás: arquivo não encontrado em "
          "dados/brutos/ (baixe o PDF pelo link em LEIA-ME_fontes.md e extraia com pdftotext -layout)")
else:
    for r in gf.itertuples():
        v = br(r.potencial_biogas_m3_ano, 0)
        check(f"bruto: goiás — potencial '{r.fonte.split(' (')[0]}' ({v}) aparece no estudo", v in panorama)
    mun_ok, mun_falha = 0, []
    for r in gm.itertuples():
        partes = [br(r.rsu_m3_ano, 0), br(r.pecuaria_m3_ano, 0)]
        if not pd.isna(r.agro_sucro_m3_ano):
            partes.append(br(r.agro_sucro_m3_ano, 0))
        linha = next((l for l in panorama.splitlines() if r.municipio.split(" (")[0] in l
                      and all(p in l for p in partes)), None)
        soma = sum(0 if pd.isna(x) else x for x in (r.rsu_m3_ano, r.pecuaria_m3_ano, r.agro_sucro_m3_ano))
        if linha and abs(soma - r.total_m3_ano) <= 1:
            mun_ok += 1
        else:
            mun_falha.append(r.municipio)
    check(f"bruto: goiás — {len(gm)} municípios: valores na mesma linha do estudo e total = soma",
          not mun_falha, f"falhas: {mun_falha}")
    for trecho in ["122 plantas", "21.620 Nm³/dia", "124 milhões de m³/ano (34,0% do total)"]:
        check(f"bruto: goiás — '{trecho}' aparece no estudo", trecho in panorama.replace("\n", " "))

# --------------------------------------------------------------------------
fails = [r for r in results if not r[1]]
for nome, ok, detalhe in results:
    print(f"{'PASS' if ok else 'FAIL'} | {nome}" + (f"  → {detalhe}" if detalhe else ""))
print("-" * 70)
print(f"Total: {len(results)} verificações · {len(results) - len(fails)} PASS · {len(fails)} FAIL")
sys.exit(1 if fails else 0)
