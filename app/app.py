# -*- coding: utf-8 -*-
"""
Radar Econômico do Biometano — Dashboard analítico
Projeto Integrador V-A · PUC-Goiás · Big Data e Inteligência Artificial
Organização parceira: 4WaTT Bio Engenharia S/A (Goiânia/GO)

Fontes:
- IEPUC-PUC-Rio, "Boletim Mensal de Acompanhamento da Indústria de Biometano
  no Brasil", Agosto de 2026 (Ed. Nº 2), com dados da ANP, MME e B3;
- Governo de Goiás (SGG) / CBIE Advisory, "Panorama do Biometano em Goiás"
  (2026), estudo técnico do Plano Estadual de Energia de Goiás 2030;
- ANP — Dados Abertos de Biometano (produção por UF, jan/2020–ago/2026);
- ANP — Levantamento de Preços de Combustíveis (diesel S10 e GNV por estado);
- IBGE — Pesquisa da Pecuária Municipal (rebanhos por estado);
- site oficial da 4WaTT (4watt.tech).
O cadastro completo (links e arquivos de cada fonte) está em dados/fontes.json.

Unidade do boletim: Mm³/d = MIL metros cúbicos por dia (notação ANP/MME;
o próprio boletim cita o "consumidor industrial de 20 Mm³/d" = 20 mil m³/dia).
No painel ela é exibida como "mil m³/d" para não haver ambiguidade.
"""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados" / "limpos"
GEOJSON_BR = DADOS / "geojson_brasil_ufs.geojson"
# cadastro das fontes de dados (nome, link e CSVs de cada uma) — ver dados/fontes.json
FONTES = {k: v for k, v in json.loads((BASE / "dados" / "fontes.json").read_text(encoding="utf-8")).items()
          if not k.startswith("_")}

st.set_page_config(
    page_title="Radar Econômico do Biometano · 4WaTT",
    page_icon="⚡",
    layout="wide",
)

# ---------------------------------------------------------------- tema
# O painel tem tema claro e escuro (.streamlit/config.toml; menu ⋮ → Settings, padrão = do
# sistema). st.context.theme pode vir errado na 1ª execução da sessão: uma 2ª execução
# imediata garante que os gráficos já saiam com as cores do tema certo.
if "tema_detectado" not in st.session_state:
    st.session_state["tema_detectado"] = True
    st.rerun()
ESCURO = st.context.theme.type == "dark"

# ---------------------------------------------------------------- estilo
# Paleta da marca 4WaTT (assets/css/theme-4watt.css do site 4watt.tech).
# Cada cor tem um significado fixo em todos os gráficos:
#   VERDE = série principal e setor sucroenergético · ROXO_SUAVE = resíduo urbano
#   (aterro/RSU) · OURO = pecuária e outros resíduos · ROXO = comparação/destaque.
# Verde × roxo × dourado diferem em matiz E luminosidade (legível com daltonismo típico).
# No tema escuro os roxos e o verde de texto são clareados para manter o contraste.
VERDE = "#03A589"
if ESCURO:
    VERDE_TXT, VERDE_CLARO = "#3FD1B3", "#1F6B5E"
    ROXO, ROXO_SUAVE = "#E3B7DC", "#C27BB6"
    OURO, OURO_TXT = "#E7BE3A", "#E7BE3A"
    CINZA, TINTA, FUNDO = "#8E8592", "#F4F1EB", "#1A1320"
    GRADE = "rgba(244,241,235,0.10)"
    SEM_DADO, BORDA = "#3A3140", "#1A1320"
    SEQ = [[0, "#0F5C50"], [0.5, VERDE], [1, ROXO]]   # mais claro = mais produção
    REGIAO_PORTF = "#1F4D45"
    COR_SEM_DADO = "cinza-escuro"
else:
    VERDE_TXT, VERDE_CLARO = "#057A64", "#9ED9CC"
    ROXO, ROXO_SUAVE = "#3A0940", "#6E2466"
    OURO, OURO_TXT = "#DBAA0F", "#9A7400"
    CINZA, TINTA, FUNDO = "#A39AA5", "#1E1822", "#FCFBF8"
    GRADE = "rgba(30,24,34,0.08)"
    # estados sem dado: bege escuro o bastante para destacar do fundo creme, divisas brancas
    SEM_DADO, BORDA = "#D9D1C4", "#FFFFFF"
    SEQ = [[0, "#BFE6DC"], [0.5, VERDE], [1, ROXO]]   # mais escuro = mais produção
    REGIAO_PORTF = "#BFE6DC"
    COR_SEM_DADO = "bege"
TEXTO_SOBRE_OURO = "#1E1822"
COR_REGIAO = {"Sudeste": VERDE, "Sul": ROXO_SUAVE, "Nordeste": OURO,
              "Centro-Oeste": VERDE_CLARO, "Norte": CINZA}
COR_MATERIA = {"Aterro sanitário": ROXO_SUAVE, "Sucroenergético": VERDE, "Outros resíduos": OURO,
               "RSU": ROXO_SUAVE, "Pecuária": OURO}
UN = "mil m³/d"
MES = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun",
       "07": "jul", "08": "ago", "09": "set", "10": "out", "11": "nov", "12": "dez"}
CAP = "Fonte: IEPUC-PUC-Rio, Boletim de Biometano — Ago/2026 (dados ANP/MME/B3)"
CAP_GO = "Fonte: Governo de Goiás (SGG) / CBIE Advisory — Panorama do Biometano em Goiás (2026)"


def rotulo_periodo(p: str) -> str:
    """'2026-08' → 'ago/26'."""
    ano, mes = p.split("-")
    return f"{MES[mes]}/{ano[2:]}"


def br(x: float, dec: int = 0) -> str:
    """Formata número no padrão brasileiro (1.368,5)."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x: float, dec: int = 1, sinal: bool = True) -> str:
    return (f"{x:+.{dec}f}%" if sinal else f"{x:.{dec}f}%").replace(".", ",")


def estilo(fig: go.Figure, altura: int, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura, separators=",.",
        margin=dict(l=10, r=10, t=10, b=10), showlegend=legenda,
        font=dict(size=13, color=TINTA, family="Inter, system-ui, sans-serif"),
        hoverlabel=dict(font_size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.15, x=0),
    )
    return fig


def mostrar(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "locale": "pt-BR"})


@st.cache_data
def _ler_csv(nome: str, modificado_em: float) -> pd.DataFrame:
    return pd.read_csv(DADOS / nome)


def carregar(nome: str) -> pd.DataFrame:
    # a data de modificação entra na chave do cache: um CSV atualizado (ex.: boletim do mês
    # seguinte) é relido sem precisar reiniciar o servidor
    return _ler_csv(nome, (DADOS / nome).stat().st_mtime)


# plotly.js 7.x só resolve `geojson` como string quando ela é chave de
# window.PlotlyGeoAssets; JSON inline deve ser passado como OBJETO.
# cache_resource: o arquivo (~2 MB) é lido uma vez, não a cada interação.
@st.cache_resource
def carregar_geojson() -> dict:
    return json.loads(GEOJSON_BR.read_text(encoding="utf-8"))


GEOJSON_OBJ = carregar_geojson()

pm = carregar("producao_mensal_2026.csv")
pm["rotulo"] = pm["periodo"].map(rotulo_periodo)
# 2025 = série REAL dos dados abertos da ANP (soma das UFs). A série "derivada" do
# crescimento a.a. publicado pelo IEPUC diverge até -11% (ago/25) porque a ANP revisou
# a base 2025 (a conferência fica em notebook/validar_dados.py). Ver
# dados/brutos/anp_abertos/PROVENIENCIA.md.
hist = carregar("producao_nacional_anp_historico.csv")
hist["rotulo"] = hist["periodo"].map(rotulo_periodo)
anp = dict(zip(hist["periodo"], hist["producao_mm3d"]))
pm["producao_2025_anp_mm3d"] = pm["periodo"].map(lambda p: anp.get(f"2025-{p[5:]}"))
pe = carregar("producao_por_estado_2026_08.csv")
mp = carregar("producao_por_materia_prima_2026_08.csv")
pu = carregar("producao_por_usina_2026_08.csv")
ut = carregar("utilizacao_capacidade_2026_08.csv")
cap = carregar("capacidade_anp.csv").sort_values("periodo")
com = carregar("comercializacao.csv")
ren = carregar("renovabio.csv")
cases = carregar("cases_4watt.csv")
uf_mes = carregar("producao_por_uf_anp_mensal.csv")      # ANP: produção por UF, 2020–2026
usinas = carregar("usinas_anp_2026_08.csv")               # ANP: 21 usinas autorizadas (ago/26)
pecuaria = carregar("potencial_pecuaria_uf_ibge.csv")     # IBGE PPM: rebanhos e potencial por UF
precos = carregar("precos_combustiveis_uf_mensal.csv")    # ANP: diesel S10 e GNV por UF
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
go_fonte = carregar("potencial_biogas_goias.csv")
go_mun = carregar("potencial_biogas_goias_municipios.csv")

d_com = dict(zip(com["indicador"], com["valor"]))
d_ren = dict(zip(ren["indicador"], ren["valor"]))
cap_atual = cap.iloc[-1]
cap_inicial = cap.iloc[0]
ult = pm.iloc[-1]
total_nac = float(ult["producao_mm3d"])

# ---------------------------------------------------------------- cabeçalho
st.markdown(f"""<style>
[data-testid="stMarkdownContainer"] table {{ display: block; overflow-x: auto; }}
[class*="st-key-insight_"] {{
    border-left: 5px solid {VERDE} !important; background: rgba(3,165,137,0.06); }}
</style>""", unsafe_allow_html=True)
st.title("⚡ Radar Econômico do Biometano")
st.caption(
    "Inteligência de mercado para apoio à decisão em projetos de biogás e biometano · "
    "Organização parceira: **4WaTT Bio Engenharia S/A** (Goiânia/GO) · "
    f"Dados de referência: **{rotulo_periodo(ult['periodo'])}** · "
    f"Unidade: **{UN}** (mil metros cúbicos por dia)"
)

# ---------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Filtros")
    periodos = pm["rotulo"].tolist()
    ini, fim = st.select_slider(
        "Período da série mensal (2026)", options=periodos,
        value=(periodos[0], periodos[-1]),
    )
    comparar_2025 = st.toggle("Comparar com 2025 (dados ANP)", value=True)
    st.divider()
    materias = st.multiselect(
        "Matérias-primas", mp["materia_prima"].tolist(), default=mp["materia_prima"].tolist(),
        help="Afeta os gráficos de composição e de utilização da capacidade (aba Produção).",
    )
    incluir_agregados = st.toggle(
        'Incluir agregados "Outros"', value=True,
        help='O boletim agrega pequenas usinas e alguns estados em "Outros".',
    )
    st.divider()
    fontes_sel = st.multiselect(
        "Fontes de dados", list(FONTES), default=list(FONTES),
        format_func=lambda k: FONTES[k]["curto"], key="fontes",
        help="Desmarque uma fonte para ocultar os gráficos e indicadores que dependem dela. "
             "O download das bases (aba Metodologia) também segue este filtro.",
    )
    st.divider()
    st.caption("Fontes: " + " · ".join(FONTES[c]["curto"] for c in fontes_sel) if fontes_sel
               else "Nenhuma fonte selecionada.")

i0, i1 = periodos.index(ini), periodos.index(fim)


def fonte_ativa(*chaves: str) -> bool:
    """True se todas as fontes estão marcadas no filtro; senão mostra um aviso no lugar."""
    faltando = [FONTES[c]["curto"] for c in chaves if c not in fontes_sel]
    if faltando:
        st.info(f"Conteúdo oculto: depende de **{', '.join(faltando)}**, desmarcada no filtro "
                "*Fontes de dados* da barra lateral.", icon="🔎")
    return not faltando


def fontes_da_aba(*chaves: str) -> None:
    st.caption("📚 Fontes desta aba: " + " · ".join(
        f"[{FONTES[c]['curto']}]({FONTES[c]['url']})" + ("" if c in fontes_sel else " *(oculta)*")
        for c in chaves))
pm_f = pm.iloc[i0:i1 + 1]

aba1, aba_reg, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "📊 Visão Geral", "🗺️ Regiões & Usinas", "🏭 Produção", "💰 Mercado",
    "📍 Oportunidades", "⚡ Portfolio 4WaTT", "📚 Metodologia",
])

# ======================================================================= 1
with aba1:
    st.subheader("O mercado de biometano no Brasil cresce rápido")
    fontes_da_aba("iepuc", "anp")

    if fonte_ativa("iepuc"):
        k = st.columns(5)
        k[0].metric(f"Produção ({UN})", br(total_nac),
                    f"{pct(ult['variacao_vs_mes_anterior_pct'])} vs mês anterior")
        k[1].metric(f"Capacidade ({UN})", br(cap_atual["autorizada_mm3d"]),
                    help="Capacidade de produção já autorizada pela ANP.")
        k[1].caption(f"mais {br(cap_atual['solicitada_mm3d'])} {UN} em "
                     f"{int(cap_atual['pedidos_em_tramitacao'])} pedidos em tramitação")
        k[2].metric("Usinas autorizadas (ANP)", int(cap_atual["usinas_concedidas"]))
        k[2].caption(f"{int(cap_atual['usinas_concedidas'] + cap_atual['pedidos_em_tramitacao'])} "
                     "somando os pedidos em tramitação")
        k[3].metric("Contratos vigentes", int(d_com["Contratos vigentes (jul/2026)"]),
                    help="Situação em jul/2026, último mês publicado do registro de contratos.")
        k[3].caption(f"de {int(d_com['Contratos registrados na ANP (jan/2014 a jul/2026)'])} "
                     "registrados desde 2014")
        k[4].metric("CBio · preço médio (R$)",
                    br(d_ren["Preço médio do CBio em ago/2026 (R$/tCO2eq)"], 2),
                    f"{pct(d_ren['Variação do preço do CBio vs mês anterior (%)'])} vs mês anterior")

        # período completo → média acumulada publicada pelo IEPUC; recorte → média simples
        media_f = (pm_f["media_acumulada_2026_mm3d"].iloc[-1] if i0 == 0
                   else pm_f["producao_mm3d"].mean())
        tem_anp = "anp" in fontes_sel
        media_25 = pm_f["producao_2025_anp_mm3d"].mean()
        aa_anp = (total_nac / anp["2025-08"] - 1) * 100
        trecho_2025 = (
            f"**{pct((media_f / media_25 - 1) * 100, 0)}** acima do mesmo período de 2025 (dados abertos "
            f"da ANP). Em {ult['rotulo']}, a alta sobre ago/25 foi de **{pct(aa_anp, 0)}** pela série da ANP "
            f"(o IEPUC publica {pct(ult['crescimento_vs_ano_anterior_pct'])}; as duas fontes divergem na "
            "base de 2025 — ver Metodologia)."
            if tem_anp else
            f"e o IEPUC publica alta de {pct(ult['crescimento_vs_ano_anterior_pct'])} em {ult['rotulo']} "
            "sobre o mesmo mês de 2025.")
        cresc_cap = (cap_atual["autorizada_mm3d"] / cap_inicial["autorizada_mm3d"] - 1) * 100
        st.markdown(
            f"**Leitura rápida.** No período selecionado (**{ini}–{fim}**) a produção média foi de "
            f"**{br(media_f)} {UN}**, {trecho_2025} A capacidade autorizada "
            f"pela ANP praticamente **dobrou** desde {rotulo_periodo(cap_inicial['periodo'])} "
            f"({pct(cresc_cap, 0)}), e o mercado segue concentrado: "
            f"**top 5 estados ≈ {br(pe[pe.uf != 'OUTROS'].producao_mm3d.sum() / total_nac * 100)}% "
            "da produção**."
        )

        st.markdown("#### Evolução da produção mensal")
        fig = go.Figure()
        if comparar_2025 and tem_anp:
            fig.add_trace(go.Scatter(
                x=pm_f["rotulo"], y=pm_f["producao_2025_anp_mm3d"], mode="lines",
                name="2025 (dados abertos ANP)",
                line=dict(color=ROXO_SUAVE, dash="dot", width=2),
                hovertemplate="%{x}: %{y:,.1f} " + UN + "<extra>2025 (ANP)</extra>",
            ))
        fig.add_trace(go.Scatter(
            x=pm_f["rotulo"], y=pm_f["producao_mm3d"], mode="lines+markers+text",
            name="2026", line=dict(color=VERDE, width=3), marker=dict(size=8),
            textfont=dict(color=VERDE_TXT),
            text=[br(v) for v in pm_f["producao_mm3d"]], textposition="top center",
            hovertemplate="%{x}: %{y:,.0f} " + UN + "<extra>2026</extra>",
        ))
        estilo(fig, 380, legenda=comparar_2025 and tem_anp)
        fig.update_yaxes(title=UN, rangemode="tozero", gridcolor=GRADE)
        fig.update_xaxes(showgrid=False)
        mostrar(fig)

    if fonte_ativa("anp"):
        per_mapa = pm_f["periodo"].iloc[-1]
        st.markdown(f"#### Brasil por estado ({rotulo_periodo(per_mapa)})")
        metrica = st.radio("Colorir o mapa por", ["Produção", "Capacidade autorizada", "Nº de usinas"],
                           horizontal=True, key="metrica_mapa",
                           help="Produção acompanha o fim do período escolhido na barra lateral; "
                                "capacidade e nº de usinas são de ago/26.")
        prod_uf = uf_mes[uf_mes["periodo"] == per_mapa].set_index("uf")["producao_mm3d"]
        cap_uf = usinas.groupby("uf").agg(cap=("capacidade_autorizada_mm3d", "sum"),
                                          n=("usina", "count"))
        mapa = (pd.DataFrame({"prod": prod_uf}).join(cap_uf, how="outer").fillna(0))
        mapa["estado"] = [next((f["properties"]["name"] for f in GEOJSON_OBJ["features"]
                                if f["id"] == u), u) for u in mapa.index]
        col_z, titulo_z = {"Produção": ("prod", UN), "Capacidade autorizada": ("cap", UN),
                           "Nº de usinas": ("n", "usinas")}[metrica]
        # corte de 0,05 mil m³/d (50 m³/d): MG registra 0,01 em ago/26 — não conta como produtor
        mapa = mapa[mapa[col_z] > (0.05 if col_z == "prod" else 0)]
        todas = [f["id"] for f in GEOJSON_OBJ["features"]]
        sem_dado = [u for u in todas if u not in mapa.index]
        nome_uf = {f["id"]: f["properties"]["name"] for f in GEOJSON_OBJ["features"]}
        motivo = {u: (f"{int(cap_uf.loc[u, 'n'])} usina(s) autorizada(s), sem produção no mês"
                      if u in cap_uf.index else "sem usina de biometano autorizada") for u in sem_dado}
        fig = go.Figure()
        fig.add_trace(go.Choropleth(
            locations=sem_dado, locationmode="geojson-id", geojson=GEOJSON_OBJ,
            z=[0] * len(sem_dado), colorscale=[[0, SEM_DADO], [1, SEM_DADO]], showscale=False,
            marker_line_color=BORDA, marker_line_width=1,
            customdata=[[nome_uf.get(u, u), motivo[u]] for u in sem_dado],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        ))
        tot_prod = float(prod_uf.sum())
        fig.add_trace(go.Choropleth(
            locations=mapa.index.tolist(), locationmode="geojson-id", geojson=GEOJSON_OBJ,
            z=mapa[col_z], zmin=0, zmax=float(mapa[col_z].max()), colorscale=SEQ,
            marker_line_color=BORDA, marker_line_width=1,
            colorbar=dict(title=dict(text=titulo_z, side="top"),
                          thickness=12, len=0.6, orientation="h", y=-0.04, yanchor="top",
                          x=0.5, xanchor="center"),
            customdata=[[r.estado, br(r.prod, 1), br(r.prod / tot_prod * 100, 1), br(r.cap, 1), int(r.n)]
                        for r in mapa.itertuples()],
            hovertemplate=("<b>%{customdata[0]}</b><br>Produção: %{customdata[1]} " + UN +
                           " (%{customdata[2]}% do total)<br>Capacidade autorizada: %{customdata[3]} " + UN +
                           "<br>%{customdata[4]} usina(s)<extra></extra>"),
        ))
        estilo(fig, 540)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=70))
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)",
                        projection_type="mercator")
        mostrar(fig)
        n_prod = int((prod_uf > 0.05).sum())
        parados = sorted(set(cap_uf.index) - set(prod_uf[prod_uf > 0.05].index))
        st.caption(
            f"{n_prod} estados produziram biometano em {rotulo_periodo(per_mapa)} e {usinas['uf'].nunique()} "
            "têm usina autorizada"
            + (f" ({', '.join(parados)} têm usina, mas não produziram no mês)" if col_z == "prod" and parados
               else "")
            + f"; os demais estados em {COR_SEM_DADO} não têm usina. Detalhe por região e usina na aba "
            "*Regiões & Usinas*. Fonte: ANP — Dados Abertos de Biometano."
        )

    if "iepuc" in fontes_sel:
        with st.container(border=True, key="insight_1"):
            st.markdown(
                """**🎯 Insight para a 4WaTT.** A produção nacional é extremamente concentrada:
em ago/26, SP (33,6%) + RJ (26,3%) ≈ **60%** do total, e os 5 maiores estados respondem por **~99%**.
**Goiás, estado-sede da 4WaTT, não produz biometano** — mas tem ~122 plantas de biogás e potencial
teórico estimado em 2,7 bi m³/ano (aba *📍 Oportunidades*). Se todos os pedidos em análise na ANP
saírem do papel, a capacidade chega a 3.391 mil m³/d até dez/2028 — 2,5× a autorizada hoje. Os
substratos fora de aterro (~20% da produção) e as regiões sem usinas são o espaço de crescimento
natural para uma empresa com engenharia própria de EPC + O&M."""
            )

# ======================================================================= regiões
with aba_reg:
    st.subheader("Regiões e usinas: o biometano ainda é Sudeste + Sul + Nordeste")
    fontes_da_aba("anp")
    if fonte_ativa("anp"):
        regs = st.multiselect("Regiões", REGIOES, default=REGIOES, key="regioes")
        us_f = usinas[usinas["regiao"].isin(regs)]
        um_f = uf_mes[uf_mes["regiao"].isin(regs)]
        ult_per = uf_mes["periodo"].max()

        k = st.columns(4)
        prod_reg_ult = um_f[um_f["periodo"] == ult_per]["producao_mm3d"].sum()
        k[0].metric(f"Produção ({UN})", br(prod_reg_ult),
                    help=f"Soma das regiões selecionadas em {rotulo_periodo(ult_per)}.")
        k[0].caption(f"{br(prod_reg_ult / uf_mes[uf_mes['periodo'] == ult_per]['producao_mm3d'].sum() * 100)}% "
                     f"do Brasil em {rotulo_periodo(ult_per)}")
        k[1].metric(f"Capacidade autorizada ({UN})", br(us_f["capacidade_autorizada_mm3d"].sum()))
        k[2].metric("Usinas autorizadas", len(us_f))
        k[2].caption(f"em {us_f['uf'].nunique()} estados")
        ociosas = us_f[us_f["uso_capacidade_biogas_pct"] < 10]
        k[3].metric("Usinas quase paradas", len(ociosas),
                    help="Processaram menos de 10% da capacidade de biogás em ago/26.")
        k[3].caption(f"{br(ociosas['capacidade_autorizada_mm3d'].sum())} {UN} de capacidade ociosa")

        colA, colB = st.columns([3, 2])
        with colA:
            st.markdown("#### Produção por região (dados abertos ANP)")
            serie = (um_f.groupby(["periodo", "regiao"], as_index=False)["producao_mm3d"].sum()
                     .pivot(index="periodo", columns="regiao", values="producao_mm3d").fillna(0))
            fig = go.Figure()
            for reg in [r for r in ["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"] if r in serie]:
                fig.add_trace(go.Scatter(
                    x=[rotulo_periodo(p) for p in serie.index], y=serie[reg], name=reg, stackgroup="r",
                    mode="lines", line=dict(width=0.8, color=COR_REGIAO[reg]),
                    hovertemplate="%{x} · " + reg + ": %{y:,.1f} " + UN + "<extra></extra>",
                ))
            estilo(fig, 360, legenda=True)
            fig.update_yaxes(title=UN, gridcolor=GRADE, rangemode="tozero")
            fig.update_xaxes(showgrid=False, nticks=10)
            mostrar(fig)
        with colB:
            st.markdown(f"#### Capacidade × produção ({rotulo_periodo(ult_per)})")
            cap_r = usinas.groupby("regiao")["capacidade_autorizada_mm3d"].sum()
            prod_r = uf_mes[uf_mes["periodo"] == ult_per].groupby("regiao")["producao_mm3d"].sum()
            ordem_r = [r for r in REGIOES if r in regs][::-1]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=ordem_r, x=[cap_r.get(r, 0) for r in ordem_r], orientation="h",
                                 name="Capacidade autorizada", marker_color=OURO,
                                 text=[br(cap_r.get(r, 0)) for r in ordem_r], textposition="outside",
                                 cliponaxis=False))
            fig.add_trace(go.Bar(y=ordem_r, x=[prod_r.get(r, 0) for r in ordem_r], orientation="h",
                                 name="Produção", marker_color=VERDE,
                                 text=[br(prod_r.get(r, 0)) for r in ordem_r], textposition="outside",
                                 cliponaxis=False))
            estilo(fig, 360, legenda=True)
            fig.update_layout(barmode="group", legend=dict(traceorder="reversed"))
            fig.update_xaxes(title=UN, gridcolor=GRADE, range=[0, max(cap_r.max(), 1) * 1.25])
            mostrar(fig)

        st.markdown("#### Usinas de biometano autorizadas pela ANP (ago/26)")
        st.dataframe(
            pd.DataFrame({
                "Usina": us_f["usina"],
                "Município/UF": us_f["municipio"] + "/" + us_f["uf"],
                "Região": us_f["regiao"],
                "Capacidade": us_f["capacidade_autorizada_mm3d"],
                "Uso": us_f["uso_capacidade_biogas_pct"],
            }).style.format({"Capacidade": lambda v: br(v, 1)}),   # vírgula decimal; ordena pelo número
            hide_index=True, width="stretch",
            column_config={
                "Usina": st.column_config.TextColumn(width="large"),
                "Capacidade": st.column_config.NumberColumn(
                    width="small", help=f"Capacidade autorizada de biometano ({UN})"),
                "Uso": st.column_config.ProgressColumn(
                    format="%d%%", min_value=0, max_value=100, width="small",
                    help="Biogás processado ÷ capacidade de processamento de biogás (ago/26)"),
            },
        )
        st.caption(f"Capacidade em {UN}. Uso = biogás processado ÷ capacidade de processamento de biogás da usina "
                   "em ago/26. Fonte: ANP — Dados Abertos de Biometano (capacidade por usina).")

        with st.container(border=True, key="insight_reg"):
            st.markdown(
                """**🎯 Insight para a 4WaTT.** A ANP registra usinas de biometano em só **9 estados**
e **nenhuma no Norte**; o **Centro-Oeste tem uma única usina** (Ivinhema/MS, 8 mil m³/d, sem
produção em ago/26) e **Goiás, nenhuma**. Capacidade autorizada não é produção: a maior usina
do país (Paulínia/SP, 226 mil m³/d) processou praticamente zero biogás no mês, e várias plantas
operam bem abaixo do que podem. Para uma empresa goiana de EPC + O&M, isso aponta duas frentes:
**abrir o mercado do Centro-Oeste** e **colocar para rodar a capacidade já autorizada**."""
            )

# ======================================================================= 2
with aba2:
    st.subheader("Estrutura da produção: aterros dominam, o resto é fronteira")
    fontes_da_aba("anp", "iepuc")

    if fonte_ativa("anp"):
        st.markdown("#### Série histórica nacional (dados abertos ANP)")
        anos = sorted({p[:4] for p in hist["periodo"]})
        ano_ini = st.select_slider("A partir de", options=anos, value=anos[0], key="ano_hist")
        hf = hist[hist["periodo"] >= f"{ano_ini}-01"]
        fig = go.Figure(go.Scatter(
            x=hf["rotulo"], y=hf["producao_mm3d"], mode="lines", line=dict(color=VERDE, width=2.5),
            fill="tozeroy", fillcolor="rgba(3,165,137,0.12)",
            hovertemplate="%{x}: %{y:,.1f} " + UN + "<extra></extra>",
        ))
        pri, fin = hf.iloc[0], hf.iloc[-1]
        fig.add_annotation(x=fin["rotulo"], y=fin["producao_mm3d"], showarrow=True, arrowhead=0,
                           arrowcolor=ROXO_SUAVE, ax=-90, ay=-28, xanchor="right",
                           text=f"{br(fin['producao_mm3d'])} ({br(fin['producao_mm3d'] / pri['producao_mm3d'], 1)}× "
                                f"{pri['rotulo']})", font=dict(color=ROXO))
        estilo(fig, 300)
        fig.update_yaxes(title=UN, rangemode="tozero", gridcolor=GRADE,
                         range=[0, hf["producao_mm3d"].max() * 1.18])
        fig.update_xaxes(showgrid=False, nticks=12)
        mostrar(fig)
        st.caption("Soma das UFs nos dados abertos da ANP, que começam em jan/2020 (a produção comercial "
                   "existe desde 2014, em Dois Arcos/RJ) e cobrem só usinas autorizadas pela ANP. "
                   "Validação cruzada: diferença < 0,5 mil m³/d em relação ao boletim IEPUC nos 8 meses "
                   "de 2026 (ver Metodologia).")

    mp_f = mp[mp["materia_prima"].isin(materias)]
    if fonte_ativa("iepuc"):
        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"#### Por matéria-prima ({ult['rotulo']})")
            if mp_f.empty:
                st.info("Selecione ao menos uma matéria-prima na barra lateral.")
            else:
                fig = go.Figure(go.Pie(
                    labels=mp_f["materia_prima"], values=mp_f["producao_mm3d"], hole=0.55,
                    sort=False, marker=dict(colors=[COR_MATERIA[m] for m in mp_f["materia_prima"]],
                                line=dict(color=FUNDO, width=2)),
                    # percentual publicado no boletim (não o recalculado pelo plotly)
                    customdata=[br(v, 1) for v in mp_f["participacao_pct"]],
                    texttemplate="%{label}<br>%{customdata}%", textposition="outside", automargin=True,
                    hovertemplate="%{label}: %{value:,.0f} " + UN + " (%{customdata}% do total)<extra></extra>",
                ))
                estilo(fig, 360)
                fig.update_layout(margin=dict(l=40, r=40, t=30, b=30))
                mostrar(fig)
            st.caption(
                "Por que só 3 grupos? É a classificação do boletim IEPUC, estimada usina a usina a partir "
                "do biogás processado (os dados abertos da ANP não informam a matéria-prima). Com só 21 "
                "usinas autorizadas, os demais substratos (dejetos animais, efluentes industriais etc.) "
                "somam 4 plantas e ficam em \"Outros resíduos\". " + CAP)
        with colB:
            st.markdown("#### Utilização da capacidade autorizada")
            rec = ["Brasil (total)", "Plantas com 1 ano ou mais de autorização"] + materias
            ut_f = ut[ut["recorte"].isin(rec)].iloc[::-1]
            curto = {"Brasil (total)": "Brasil", "Plantas com 1 ano ou mais de autorização": "Plantas com 1 ano+"}
            fig = go.Figure(go.Bar(
                y=[curto.get(r, r) for r in ut_f["recorte"]], x=ut_f["taxa_utilizacao_pct"], orientation="h",
                marker_color=[ROXO if r.startswith("Brasil") else VERDE_CLARO if "1 ano" in r
                              else COR_MATERIA[r] for r in ut_f["recorte"]],
                text=[pct(v, 1, sinal=False) for v in ut_f["taxa_utilizacao_pct"]],
                textposition="outside", cliponaxis=False,
                customdata=[pct(v) for v in ut_f["var_vs_mes_anterior_pct"]],
                hovertemplate="%{y}: %{x:.1f}% (var. %{customdata} vs mês ant.)<extra></extra>",
            ))
            estilo(fig, 360)
            fig.update_xaxes(range=[0, 72], ticksuffix="%", gridcolor=GRADE)
            mostrar(fig)
            st.caption("Taxa de utilização em ago/26. O parque de usinas, somado, opera a **38,7%** da "
                       "capacidade autorizada — demanda latente por O&M e otimização. " + CAP)

        st.markdown(f"#### Produção por usina ({ult['rotulo']})")
        c1, c2 = st.columns([1, 2])
        ordem = c1.radio("Ordenar por", ["Produção", "Variação vs mês anterior"], horizontal=True)
        top_n = c2.slider("Quantidade de usinas", 3, len(pu), len(pu))
        pu_f = pu if incluir_agregados else pu[~pu["usina"].str.startswith("Outros")]
        col_ord = "producao_mm3d" if ordem == "Produção" else "crescimento_vs_mes_anterior_pct"
        pu_f = pu_f.sort_values(col_ord, ascending=False).head(top_n).iloc[::-1]  # maior no topo
        nome_curto = {"Orizon Biometano Jaboatão dos Guararapes": "Orizon Jaboatão",
                      "Outros (agregado de pequenas usinas)": "Outros (agregado)"}
        fig = go.Figure(go.Bar(
            y=[nome_curto.get(u, u) for u in pu_f["usina"]], x=pu_f["producao_mm3d"], orientation="h",
            marker_color=[CINZA if u.startswith("Outros") else VERDE for u in pu_f["usina"]],
            # variação em texto colorido ao lado da barra (cor só sinaliza o sentido)
            text=[f"{br(v, 1)}  <span style='color:{VERDE_TXT if g >= 0 else ROXO_SUAVE}'>{pct(g)}</span>"
                  for v, g in zip(pu_f["producao_mm3d"], pu_f["crescimento_vs_mes_anterior_pct"])],
            textposition="outside", cliponaxis=False,
            customdata=pu_f["usina"],
            hovertemplate="%{customdata}<br>%{x:,.1f} " + UN + "<extra></extra>",
        ))
        estilo(fig, 60 + 34 * len(pu_f))
        fig.update_xaxes(title=f"{UN} (rótulo: produção · variação vs mês anterior)",
                         range=[0, pu["producao_mm3d"].max() * 1.45], gridcolor=GRADE)
        mostrar(fig)

        st.dataframe(
            pd.DataFrame({
                "Matéria-prima": mp_f["materia_prima"], "Usinas": mp_f["num_usinas"].astype(str),
                f"Produção ({UN})": [br(v) for v in mp_f["producao_mm3d"]],
                "Participação": [pct(v, 1, sinal=False) for v in mp_f["participacao_pct"]],
                "Var. vs mês anterior": [pct(v) for v in mp_f["crescimento_vs_mes_anterior_pct"]],
            }),
            hide_index=True, width="stretch",
        )

        with st.container(border=True, key="insight_2"):
            st.markdown(
                """**🎯 Insight para a 4WaTT.** ~80% da produção nacional vem de **aterros
sanitários**; o setor sucroenergético responde por ~19%. Quase toda a matriz de resíduos
que a 4WaTT atende (suínos, bovinos, aves, frigoríficos, usinas de etanol) está nos ~20% fora de
aterro — e a parte agropecuária e industrial ("Outros resíduos") soma só ~1% e oscila muito mês a
mês (-91% em ago/26). A baixa utilização da capacidade do parque (**38,7%**; sucroenergético **27,2%**) reforça
que o gargalo não é só construir usinas, mas **operá-las bem** — o espaço do O&M."""
            )

# ======================================================================= 3
with aba3:
    st.subheader("Comercialização: o mercado já compra — e o carbono agrega receita")
    fontes_da_aba("iepuc")

    if fonte_ativa("iepuc"):
        k = st.columns(4)
        k[0].metric("Contratos registrados (ANP)",
                    int(d_com["Contratos registrados na ANP (jan/2014 a jul/2026)"]))
        k[1].metric("Transações anunciadas",
                    int(d_com["Transações anunciadas identificadas no Brasil (jan/2014 a ago/2026)"]))
        k[1].caption(f"{int(d_com['Transações com compradores do setor industrial'])} com compradores "
                     "industriais")
        k[0].caption("desde 2014 (jan/2014–jul/2026)")
        k[2].metric("CBio · preço médio (R$)",
                    br(d_ren["Preço médio do CBio em ago/2026 (R$/tCO2eq)"], 2),
                    f"{pct(d_ren['Variação do preço do CBio vs mês anterior (%)'])} vs mês anterior")
        # intensidade de carbono maior é PIOR → cor invertida (alta em vermelho)
        k[3].metric("Carbono (gCO₂eq/MJ)",
                    br(d_ren["Intensidade de carbono média das usinas certificadas (gCO2eq/MJ)"], 2),
                    f"{pct(d_ren['Variação da intensidade de carbono média vs mês anterior (%)'])} vs mês anterior",
                    delta_color="inverse")
        k[3].caption(f"intensidade média · {int(d_ren['Usinas de biometano certificadas no RenovaBio (ago/2026)'])} "
                     "usinas certificadas no RenovaBio")

        colA, colB = st.columns(2)
        with colA:
            st.markdown("#### Modal logístico das transações anunciadas")
            n_gnc = int(d_com["Entregas por GNC (veículo)"])
            n_gas = int(d_com["Entregas por gasoduto de distribuição"])
            fig = go.Figure(go.Bar(
                y=["Gasoduto de distribuição", "GNC (veículo)"], x=[n_gas, n_gnc], orientation="h",
                marker_color=[ROXO_SUAVE, VERDE],
                text=[f"{n_gas} ({br(n_gas / (n_gas + n_gnc) * 100)}%)",
                      f"{n_gnc} ({br(n_gnc / (n_gas + n_gnc) * 100)}%)"],
                textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{x} transações<extra></extra>",
            ))
            estilo(fig, 300)
            fig.update_xaxes(title="transações (2014–ago/26)",
                             range=[0, n_gnc * 1.35], gridcolor=GRADE)
            mostrar(fig)
            st.caption("GNC = gás comprimido transportado por caminhão: viabiliza usinas longe da "
                       "rede de gasodutos, como no interior de Goiás. " + CAP)
        with colB:
            st.markdown("#### Capacidade: autorizada × em tramitação (ANP)")
            rot = cap["periodo"].map(rotulo_periodo)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=rot, y=cap["autorizada_mm3d"], name="Autorizada", marker_color=VERDE,
                                 text=[br(v) for v in cap["autorizada_mm3d"]], textposition="inside",
                                 textfont=dict(color="#FFFFFF"),
                                 hovertemplate="%{x}: %{y:,.0f} " + UN + "<extra>Autorizada</extra>"))
            fig.add_trace(go.Bar(x=rot, y=cap["solicitada_mm3d"], name="Em tramitação",
                                 marker_color=OURO,
                                 text=[br(v) for v in cap["solicitada_mm3d"]], textposition="inside",
                                 textfont=dict(color=TEXTO_SOBRE_OURO),
                                 hovertemplate="%{x}: %{y:,.0f} " + UN + "<extra>Em tramitação</extra>"))
            estilo(fig, 300, legenda=True)
            fig.update_layout(barmode="stack")
            fig.update_yaxes(title=UN, gridcolor=GRADE, tickformat=",.0f")
            mostrar(fig)
            st.caption("Total de ago/26 (3.391 mil m³/d) = capacidade estimada pelo IEPUC para dez/2028, caso "
                       "todos os pedidos em tramitação entrem em operação no prazo. " + CAP)

        st.markdown("#### RenovaBio & CBios (linha de receita de carbono)")
        st.dataframe(pd.DataFrame({
            "Indicador": ren["indicador"],
            "Valor (ago/26)": [f"{v:g}".replace(".", ",") for v in ren["valor"]],
            "Fonte": ren["fonte"],
        }), hide_index=True, width="stretch")

        with st.container(border=True, key="insight_3"):
            st.markdown(
                """**Negociações em destaque no mês (boletim ago/26):** Unilever ampliou parceria com a
comercializadora Edge — biometano do aterro de Paulínia/SP abastecerá fábrica em Aguaí/SP
(1.125 m³/dia); Regenera Rio (Aegea) inaugurou frota de 60 carretas movidas a GNV, abastecidas
com biometano da Gás Verde no aterro de Seropédica/RJ. **🎯 Insight para a 4WaTT:** o setor industrial concentra 30 das 55 transações
anunciadas — frigoríficos, curtumes e indústrias de alimentos são simultaneamente compradores
potenciais e geradores de substrato, perfil exato do portfolio EPC/O&M da 4WaTT. O CBio
(R\\$ 24,53 em ago/26; 1 crédito = 1 tCO₂eq evitada) agrega uma segunda receita para a usina
certificada no RenovaBio."""
            )

# ======================================================================= 4
with aba4:
    st.subheader("Onde está a oportunidade: potencial, preço e Goiás")
    fontes_da_aba("ibge", "anp_precos", "goias")

    # ---------------------------------------------------------- potencial pecuário (IBGE)
    st.markdown("#### Potencial de biogás da pecuária por estado")
    if fonte_ativa("ibge"):
        ano_pec = int(pecuaria["ano"].iloc[0])
        rebanho = st.radio("Rebanho", ["Total", "Suínos", "Aves", "Vacas ordenhadas"],
                           horizontal=True, key="rebanho")
        col_p = {"Total": "biogas_total_m3_ano", "Suínos": "biogas_suinos_m3_ano",
                 "Aves": "biogas_aves_m3_ano", "Vacas ordenhadas": "biogas_vacas_m3_ano"}[rebanho]
        pec = pecuaria.assign(v=pecuaria[col_p] / 1e6).sort_values("v", ascending=False)
        pec["pos"] = range(1, len(pec) + 1)
        go_pos = int(pec.loc[pec.uf == "GO", "pos"].iloc[0])
        colA, colB = st.columns([3, 2])
        with colA:
            fig = go.Figure(go.Choropleth(
                locations=pec["uf"], locationmode="geojson-id", geojson=GEOJSON_OBJ, z=pec["v"],
                zmin=0, colorscale=SEQ, marker_line_color=BORDA, marker_line_width=1,
                colorbar=dict(title=dict(text="mi m³/ano", side="top"), thickness=12, len=0.6,
                              orientation="h", y=-0.04, yanchor="top", x=0.5, xanchor="center"),
                customdata=pec[["estado", "pos"]],
                hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]}º)<br>%{z:,.0f} milhões m³ de "
                              "biogás/ano<extra></extra>",
            ))
            estilo(fig, 460)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=70))
            fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)",
                            projection_type="mercator")
            mostrar(fig)
        with colB:
            top = pec.head(10).iloc[::-1]
            fig = go.Figure(go.Bar(
                y=[f"{r.pos}º {r.uf}" for r in top.itertuples()], x=top["v"], orientation="h",
                marker_color=[ROXO if u == "GO" else OURO for u in top["uf"]],
                text=[br(v) for v in top["v"]], textposition="outside", cliponaxis=False,
                customdata=top["estado"],
                hovertemplate="%{customdata}: %{x:,.0f} milhões m³/ano<extra></extra>",
            ))
            estilo(fig, 460)
            fig.update_xaxes(title="milhões de m³ de biogás/ano", gridcolor=GRADE,
                             range=[0, top["v"].max() * 1.25])
            mostrar(fig)
        st.caption(
            f"Potencial teórico estimado com os rebanhos do IBGE ({ano_pec}) e os coeficientes por animal "
            "do estudo de Goiás (aves 0,0014 · suínos 0,240 · vacas ordenhadas 0,360 m³ de biogás por "
            "cabeça por dia); aplicado ao IBGE de 2023, o método reproduz o número do estudo para Goiás "
            "com diferença menor que 1%. Fonte: IBGE — Pesquisa da Pecuária Municipal.")
        pos_go = {nome: int(pecuaria[c].rank(ascending=False, method="min")[pecuaria.uf == "GO"].iloc[0])
                  for nome, c in (("vacas ordenhadas", "biogas_vacas_m3_ano"),
                                  ("suínos", "biogas_suinos_m3_ano"), ("aves", "biogas_aves_m3_ano"))}
        lideres = ", ".join(pec["uf"].head(3))
        outros = " e ".join(f"{p}º em {n}" for n, p in sorted(
            ((n, p) for n, p in pos_go.items() if n != "vacas ordenhadas"), key=lambda x: x[1]))
        with st.container(border=True, key="insight_pec"):
            st.markdown(
                f"""**🎯 Insight para a 4WaTT.** Em potencial de biogás da pecuária ({rebanho.lower()}),
os líderes são {lideres}; **Goiás é o {go_pos}º do Brasil** e não tem nenhuma usina de biometano
autorizada. O destaque goiano são as **vacas ordenhadas ({pos_go['vacas ordenhadas']}º do país)**; o estado
fica em {outros}. São dejetos que a matriz de resíduos da 4WaTT atende.""")

    # ---------------------------------------------------------- preço dos concorrentes (ANP)
    st.markdown("#### Quanto vale 1 m³ de biometano: diesel × GNV")
    if fonte_ativa("anp_precos"):
        ult_p = precos["periodo"].max()
        ufs_p = sorted(precos["uf"].unique())
        sel_uf = st.multiselect("Estados", ufs_p, default=["GO", "SP"], max_selections=4, key="ufs_preco")
        p_ult = precos[precos["periodo"] == ult_p]
        diesel_go = p_ult[(p_ult.uf == "GO") & (p_ult.produto == "Diesel S10")]
        gnv_ult = p_ult[p_ult.produto == "GNV"]
        k = st.columns(3)
        if len(diesel_go):
            d = diesel_go.iloc[0]
            k[0].metric(f"Diesel S10 em GO ({rotulo_periodo(ult_p)}, R\\$/l)", br(d.preco_revenda, 2))
            k[1].metric("1 m³ de biometano substitui (R\\$)", br(d.preco_m3_biometano_eq, 2),
                        help="Diesel evitado: 1 m³ de biometano ≈ 0,87 l de diesel (CIBiogás).")
        k[2].metric("GNV médio nos estados com GNV (R\\$/m³)", br(gnv_ult["preco_revenda"].mean(), 2))
        k[2].caption(f"{gnv_ult.uf.nunique()} estados têm GNV pesquisado em {rotulo_periodo(ult_p)}"
                     + ("; Goiás não" if "GO" not in set(gnv_ult.uf) else ""))
        fig = go.Figure()
        traco = ["solid", "dash", "dot", "dashdot"]
        meses_p = sorted(precos["periodo"].unique())
        for i, uf in enumerate(sel_uf):
            for prod, cor in (("Diesel S10", ROXO_SUAVE), ("GNV", VERDE)):
                q = precos[(precos.uf == uf) & (precos.produto == prod)]
                if q.empty:
                    continue
                # meses sem pesquisa ficam vazios (a linha quebra, sem ligar pontos distantes);
                # séries esparsas aparecem como marcadores
                q = q.set_index("periodo").reindex(meses_p)
                esparsa = q["preco_m3_biometano_eq"].notna().sum() < 12
                fig.add_trace(go.Scatter(
                    x=[rotulo_periodo(x) for x in q.index], y=q["preco_m3_biometano_eq"],
                    name=f"{prod} — {uf}" + (" (registros esporádicos)" if esparsa else ""),
                    mode="markers" if esparsa else "lines", connectgaps=False,
                    marker=dict(color=cor, size=7), line=dict(color=cor, width=2.2, dash=traco[i]),
                    hovertemplate="%{x} · " + f"{prod} {uf}" + ": R$ %{y:,.2f} por m³ eq.<extra></extra>",
                ))
        estilo(fig, 380, legenda=True)
        fig.update_yaxes(title="R$ por m³ de biometano equivalente", gridcolor=GRADE, rangemode="tozero")
        fig.update_xaxes(showgrid=False, nticks=12)
        mostrar(fig)
        st.caption("Diesel convertido para R\\$ por m³ de biometano equivalente (× 0,87 l/m³); GNV já em R\\$/m³. "
                   "Estados sem linha de GNV não têm o combustível na pesquisa da ANP. Preço médio de "
                   "revenda. Fonte: ANP — Levantamento de Preços de Combustíveis.")
        gnv_go = precos[(precos.uf == "GO") & (precos.produto == "GNV")]
        if len(diesel_go) and len(gnv_ult) and "GO" not in set(gnv_ult.uf):
            g_max = gnv_ult.loc[gnv_ult["preco_revenda"].idxmax()]
            comp = ("acima" if d.preco_m3_biometano_eq > g_max.preco_revenda
                    else "abaixo")
            with st.container(border=True, key="insight_preco"):
                st.markdown(
                    f"""**🎯 Insight para a 4WaTT.** Goiás **praticamente não tem GNV**: desde 2020, a pesquisa
de preços da ANP registrou o combustível no estado só {len(gnv_go)} vezes, em meses esparsos — e
nenhuma em {rotulo_periodo(ult_p)}. Não há mercado de gás veicular para o biometano disputar. Lá, ele
concorre com o **diesel**: cada m³ substitui cerca de 0,87 l, o que vale **R\\$ {br(d.preco_m3_biometano_eq, 2)}**
ao preço goiano de {rotulo_periodo(ult_p)} — {comp} do GNV mais caro do país no mês
({g_max.uf}, R\\$ {br(g_max.preco_revenda, 2)}/m³). Para frotas, agroindústria e transportadoras goianas, o
argumento de viabilidade é a troca de diesel, com o biometano levado por caminhão (GNC).""")

    # ---------------------------------------------------------- Goiás (estudo estadual)
    st.markdown("#### Goiás em detalhe (estudo estadual)")
    if fonte_ativa("goias"):
        st.markdown(
            "Estudo técnico do **Plano Estadual de Energia de Goiás 2030** (Governo de Goiás/SGG e "
            "CBIE Advisory) estima o potencial **teórico** de biogás do estado por fonte e município. "
            "Cruzado com o boletim nacional, ele indica onde está a oportunidade."
        )

        pot_total = go_fonte["potencial_biogas_m3_ano"].sum()
        k = st.columns(4)
        k[0].metric("Biogás (bi m³/ano)", br(pot_total / 1e9, 2),
                    help="Potencial teórico estimado pelo estudo; não é produção viável.")
        k[0].caption("potencial teórico; ≈ 1,7 bi m³/ano de biometano (estimativa do estudo)")
        k[1].metric(f"Potencial de biometano ({UN})", br(1.7e9 / 365 / 1000))
        k[1].caption(f"≈ {br(1.7e9 / 365 / 1000 / total_nac, 1)}× a produção nacional de {ult['rotulo']}")
        k[2].metric("Plantas de biogás em Goiás", "~122")
        k[2].caption("112 agropecuárias · 7 industriais · 3 RSU/esgoto (CIBiogás 2025, citado no estudo)")
        k[3].metric("Biometano em projeto (Nm³/d)", "21.620")
        k[3].caption("Plantas em Edéia e Rio Verde (dados ANP citados no estudo)")

        colA, colB = st.columns([2, 3])
        with colA:
            st.markdown("#### Potencial por fonte de resíduo")
            gf = go_fonte.sort_values("potencial_biogas_m3_ano")
            fig = go.Figure(go.Bar(
                y=[f.split(" (")[0] for f in gf["fonte"]], x=gf["potencial_biogas_m3_ano"] / 1e6,
                orientation="h", marker_color=[ROXO_SUAVE if f.startswith("Resíduos") else
                                               OURO if f.startswith("Pecuária") else VERDE
                                               for f in gf["fonte"]],
                text=[f"{br(v / 1e6)} mi ({br(v / pot_total * 100)}%)" for v in gf["potencial_biogas_m3_ano"]],
                textposition="outside", cliponaxis=False,
                customdata=gf["observacao"],
                hovertemplate="%{y}: %{x:,.0f} milhões m³/ano<br>%{customdata}<extra></extra>",
            ))
            estilo(fig, 300)
            fig.update_xaxes(title="milhões de m³ de biogás/ano", range=[0, 3700], gridcolor=GRADE,
                             tickformat=",.0f")
            mostrar(fig)
        with colB:
            st.markdown("#### Municípios com maior potencial")
            c1, c2 = st.columns(2)
            fonte_sel = c1.selectbox("Fonte", ["Todas", "Sucroenergético", "Pecuária", "RSU"])
            n_mun = c2.slider("Municípios", 5, len(go_mun), 10)
            col = {"Todas": "total_m3_ano", "Sucroenergético": "agro_sucro_m3_ano",
                   "Pecuária": "pecuaria_m3_ano", "RSU": "rsu_m3_ano"}[fonte_sel]
            gm = go_mun.dropna(subset=[col]).sort_values(col, ascending=False).head(n_mun).iloc[::-1]
            series = ([("rsu_m3_ano", "RSU", COR_MATERIA["RSU"]),
                       ("pecuaria_m3_ano", "Pecuária", COR_MATERIA["Pecuária"]),
                       ("agro_sucro_m3_ano", "Sucroenergético", COR_MATERIA["Sucroenergético"])]
                      if fonte_sel == "Todas" else [(col, fonte_sel, COR_MATERIA[fonte_sel])])
            fig = go.Figure()
            for c, nome, cor in series:
                fig.add_trace(go.Bar(
                    y=gm["municipio"], x=gm[c].fillna(0) / 1e6, name=nome, orientation="h",
                    marker_color=cor,
                    hovertemplate="%{y} · " + nome + ": %{x:,.1f} mi m³/ano<extra></extra>",
                ))
            estilo(fig, 90 + 30 * len(gm), legenda=fonte_sel == "Todas")
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.02, yanchor="bottom",
                                                           x=0, traceorder="normal"))
            fig.update_xaxes(title="milhões de m³ de biogás/ano", gridcolor=GRADE)
            mostrar(fig)
        st.caption("Rio Verde: potencial sucroenergético não detalhado na tabela do estudo (total = RSU + "
                   "pecuária). Potencial teórico ≠ produção viável: não considera logística, escala ou "
                   "custos. " + CAP_GO)

        with st.container(border=True, key="insight_4"):
            st.markdown(
                """**🎯 Insight para a 4WaTT.** (1) **Goiânia — sede da empresa e local do CEASA — é o
município com maior potencial de biogás de RSU do estado** (124 milhões m³/ano, 34% do RSU
goiano): a operação do CEASA é vitrine para replicar o modelo em resíduos urbanos.
(2) O potencial **pecuário** (402 milhões m³/ano no estudo, com rebanhos de 2023) é **disperso** — os 30 maiores municípios somam
só 32% —, o que favorece plantas descentralizadas de médio porte, exatamente o formato EPC + O&M.
(3) O **sucroenergético** (vinhaça, torta de filtro) concentra 72% do potencial: parcerias com
usinas de etanol do sul e sudoeste goianos (Goiatuba, Edéia, Mineiros, Caçu — os 4 maiores
potenciais) são a frente de maior escala."""
            )

# ======================================================================= 5
with aba5:
    st.subheader("Portfolio da 4WaTT no contexto nacional")
    fontes_da_aba("4watt")
    if fonte_ativa("4watt"):
        estagios = st.multiselect("Estágio dos projetos", sorted(cases["estagio"].unique()),
                                  default=sorted(cases["estagio"].unique()))
        cs = cases[cases["estagio"].isin(estagios)].reset_index(drop=True)
        cs.insert(0, "nº", range(1, len(cs) + 1))

        # coordenadas (aproximadas, da sede do município) vêm do próprio CSV;
        # projeto sem coordenada fica fora do mapa, mas continua na tabela.
        # Projetos na mesma cidade viram um único marcador ("2 · 3") — sem rótulos sobrepostos.
        pts = (cs.dropna(subset=["lat", "lon"])
               .groupby(["lat", "lon", "cidade"], as_index=False)
               .agg(nums=("nº", lambda s: " · ".join(map(str, s))),
                    nomes=("projeto", lambda s: "<br>".join(s))))
        regiao = {"GO", "SP", "MG", "RJ", "DF", "MS", "MT", "BA", "TO"}
        feats = [f for f in GEOJSON_OBJ["features"] if f.get("id") in regiao]
        geo_reg = {**GEOJSON_OBJ, "features": feats}
        fig = go.Figure()
        fig.add_trace(go.Choropleth(
            locations=[f["id"] for f in feats], locationmode="geojson-id", geojson=geo_reg,
            z=[1 if f["id"] in ("GO", "SP") else 0 for f in feats],
            colorscale=[[0, SEM_DADO], [1, REGIAO_PORTF]], showscale=False,
            marker_line_color=BORDA, marker_line_width=1.2,
            text=[f["properties"]["name"] for f in feats],
            hovertemplate="%{text}<extra></extra>",
        ))
        fig.add_trace(go.Scattergeo(
            lat=[-15.2, -22.3], lon=[-50.5, -49.3], mode="text", text=["GOIÁS", "SÃO PAULO"],
            textfont=dict(size=12, color=VERDE_TXT), hoverinfo="skip",
        ))
        fig.add_trace(go.Scattergeo(
            lat=pts["lat"], lon=pts["lon"], mode="markers+text", text=pts["nums"],
            textfont=dict(color=FUNDO if ESCURO else "#FFFFFF", size=12), textposition="middle center",
            marker=dict(size=[34 if "·" in n else 26 for n in pts["nums"]], color=ROXO, opacity=1,
                        line=dict(color=FUNDO, width=2)),
            customdata=pts[["cidade", "nomes"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        ))
        # rótulo da cidade ao lado do marcador; Palmeiras (a oeste de Goiânia) à esquerda
        lado = ["middle left" if c.startswith("Palmeiras") else "middle right" for c in pts["cidade"]]
        desloc = [-0.35 if l == "middle left" else 0.35 for l in lado]
        fig.add_trace(go.Scattergeo(
            lat=pts["lat"], lon=pts["lon"] + pd.Series(desloc), mode="text", text=pts["cidade"],
            textposition=lado, textfont=dict(size=13, color=TINTA), hoverinfo="skip",
        ))
        estilo(fig, 480)
        fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                        lonaxis_range=[-54, -45], lataxis_range=[-23.2, -14.6])
        mostrar(fig)
        st.caption("Coordenadas aproximadas (sede do município). Passe o mouse sobre os marcadores "
                   "para ver os projetos.")

        md = ["| nº | Projeto | Cidade/UF | Substrato | Estágio | Destaque (informação pública) |",
              "|---|---|---|---|---|---|"]
        for _, r in cs.iterrows():
            cel = {k: str(r[k]).replace("|", "\\|").replace("$", "\\$") for k in
                   ("projeto", "cidade", "substrato", "estagio", "destaque")}
            md.append(f"| **{r['nº']}** | {cel['projeto']} | {cel['cidade']} | {cel['substrato']} "
                      f"| {cel['estagio']} | {cel['destaque']} |")
        st.markdown("\n".join(md))

        with st.container(border=True, key="insight_5"):
            st.markdown(
                """**🎯 Leitura estratégica.** O portfolio cobre as três frentes do funil que o mercado
nacional está atravessando: **(1)** operação — O&M com indicadores em tempo real no CEASA Goiás;
**(2)** construção — UTB Franca (curtume→biometano) com obras em estágio avançado e licença ambiental emitida;
**(3)** projeto industrial — Frigorífico Franca, em operação com 2.800 Nm³/dia de biogás. Enquanto o
mercado nacional se concentra em aterros (SP/RJ), a 4WaTT constrói reputação em resíduos orgânicos,
industriais e agroindustriais — segmento minoritário no mercado (~20% da produção fora de aterros) e de maior aderência ao modelo
EPC + O&M + receita recorrente."""
            )

# ======================================================================= 6
with aba6:
    st.subheader("Metodologia, fontes e limitações")

    st.markdown("""
**Objetivo analítico.** Transformar dados públicos de mercado em leitura estruturada para
apoiar decisões comerciais e técnicas da 4WaTT (priorização de substratos/regiões, narrativa
de EVTE e comunicação a investidores).

**Público e decisões apoiadas.** Diretoria e equipes comercial/técnica da 4WaTT: onde prospectar
(estado × substrato), como dimensionar a narrativa de viabilidade (crescimento + CBio) e o que
monitorar mês a mês (pipeline ANP, utilização da capacidade).

### Fontes
O filtro **Fontes de dados**, na barra lateral, oculta os gráficos de cada fonte; cada aba indica,
logo abaixo do título, de quais fontes depende.

| # | Fonte | Uso no painel |
|---|-------|---------------|
| 1 | IEPUC-PUC-Rio — *Boletim Mensal de Acompanhamento da Indústria de Biometano no Brasil*, **Ago/2026, Ed. Nº 2** (dados ANP, MME, B3) | Produção mensal/por estado/matéria-prima/usina; utilização da capacidade; capacidade autorizada; contratos; transações; CBios |
| 2 | **ANP — Dados Abertos de Biometano** (produção por UF e capacidade por usina, jan/2020–ago/2026) | Série histórica nacional; linha de 2025; validação cruzada dos números do boletim |
| 3 | **ANP — Levantamento de Preços de Combustíveis** (série mensal por estado, 2020–2026) | Diesel S10 e GNV por estado; valor de 1 m³ de biometano como substituto |
| 4 | **IBGE — Pesquisa da Pecuária Municipal** (rebanhos por estado, 2025) | Potencial de biogás da pecuária em todos os estados |
| 5 | Governo de Goiás (SGG) / CBIE Advisory — *Panorama do Biometano em Goiás* (2026), estudo do PEEG 2030 | Potencial de biogás por fonte e município em Goiás; plantas de biogás (CIBiogás 2025) e de biometano em desenvolvimento no estado |
| 6 | Site oficial da 4WaTT (4watt.tech) — página inicial, *Solução Biogás* e páginas de cases | Portfolio de projetos da organização |
| 7 | Code for America — malha GeoJSON das UFs | Mapas |

### Premissas e convenções
- **Unidade:** o boletim usa **Mm³/d = mil m³ por dia** (notação ANP/MME); o painel exibe "mil m³/d".
- Participações percentuais por estado recalculadas a partir da produção absoluta quando o
  arredondamento do texto do boletim difere.
- **Linha de 2025 = dados abertos da ANP.** Os níveis de 2025 implícitos no crescimento anual
  publicado pelo IEPUC não coincidem com a série atual da ANP (ago/25: 344 × 386 mil m³/d),
  provavelmente por revisão da base de 2025 entre edições. Com a série da ANP, ago/26 fica +37%
  sobre ago/25 (IEPUC: +53,7%) e a média jan–ago/26, +54%. Os valores de **2026** coincidem
  nas duas fontes (diferença < 0,5 mil m³/d por mês).
- **Escopo: biometano, não biogás.** O painel acompanha o biometano (biogás purificado, ~95–99%
  de metano, equivalente ao gás natural), regulado pela ANP. As plantas de biogás da 4WaTT
  seguem outra regulação e por isso não aparecem entre as 21 usinas autorizadas da ANP.
- O potencial de Goiás é **teórico** (estimativa do estudo); não equivale a produção viável.
- **Potencial da pecuária por estado:** rebanhos do IBGE (2025) × coeficientes por animal do estudo de
  Goiás (aves 0,0014 · suínos 0,240 · vacas ordenhadas 0,360 m³ de biogás por cabeça por dia).
  Aplicado ao IBGE de 2023, o método reproduz o número do estudo para Goiás com diferença < 1%.
- **Preços:** o diesel é convertido em R\\$ por m³ de biometano equivalente pelo fator do CIBiogás citado
  no estudo de Goiás (1 m³ de biometano ≈ 0,87 l de diesel); o GNV já é cotado em R\\$/m³.
- Os números foram conferidos contra as publicações originais (totais, somas, participações,
  crescimentos e consistência entre as fontes).

### Limitações
- A base de transações do IEPUC-Rio é compilada de notícias e relatórios públicos: **não é exaustiva**.
- O registro da ANP cobre apenas contratos de biometano dentro da especificação regulatória.
- O boletim não detalha as UFs do agregado "Outros". Os dados abertos da ANP trazem UF e município
  de cada usina, mas **não informam a matéria-prima**.
- **Matérias-primas em 3 grupos** (aterro sanitário, sucroenergético, outros resíduos): é a
  classificação do IEPUC, estimada a partir do biogás processado por usina. Como só há 21 usinas
  de biometano autorizadas, os demais substratos (dejetos animais, efluentes industriais,
  resíduos agroindustriais) somam 4 plantas e ficam agregados em "Outros resíduos".
- **Período coberto:** a série da ANP começa em **jan/2020**, primeiro ano publicado pela agência
  (o Anuário Estatístico 2025 também traz a produção de biometano só a partir de 2020). Havia
  produção antes: Dois Arcos/RJ opera desde 2014 e GNR Fortaleza/CE desde 2018. Em jan/2020 só a
  GNR Fortaleza estava autorizada; Gás Verde e Dois Arcos entraram em jul/2020.
- **Cobertura:** a ANP registra só as usinas **autorizadas** por ela. Estudo do BNDES (2024) estima
  ~400 mil m³/d produzidos em 2022 por 20 plantas com purificação, contra média de ~183 mil m³/d
  das 4–5 usinas autorizadas na série da ANP — o volume fora da regulação não aparece aqui.
- O mapa do portfolio usa coordenadas aproximadas (sede do município).
- Dados de referência: **agosto/2026** (boletim publicado em 28/09/2026).

### Tecnologias
Python · Pandas · Plotly · Streamlit (open source, conforme orientado na proposta).
""")

    # o pacote de download segue o filtro de fontes
    arquivos = sorted({a for c in fontes_sel for a in FONTES[c]["arquivos"]})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in arquivos:
            z.write(DADOS / nome, nome)
    st.download_button(f"⬇️ Baixar as bases das fontes selecionadas ({len(arquivos)} CSVs, .zip)",
                       buf.getvalue(), file_name="radar_biometano_dados.zip", mime="application/zip",
                       disabled=not arquivos)
    st.caption("Projeto Integrador V-A — PUC-Goiás · Curso de Big Data e Inteligência Artificial · "
               "Parceria extensionista: 4WaTT Bio Engenharia S/A")
