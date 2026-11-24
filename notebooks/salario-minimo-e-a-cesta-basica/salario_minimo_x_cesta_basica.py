import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import pandas as pd

    from playground import PROCESSED_DIR, RAW_DIR

    CESTA = PROCESSED_DIR / "cesta-basica-br" / "cesta_basica_capitais.parquet"
    SALARIO = RAW_DIR / "salario-minimo" / "salario-minimo_nominal_e_real.csv"

    # Paleta categórica de referência (slots 1 e 2) + tinta neutra
    AZUL, LARANJA, NEUTRO = "#2a78d6", "#eb6834", "#898781"
    VERDE = "#008300"  # slot 6: poder de compra
    VERMELHO = "#e34948"  # polo negativo do par divergente (azul ↔ vermelho)
    HORAS_MES = 220  # jornada legal mensal usada pelo DIEESE
    return (
        AZUL,
        CESTA,
        HORAS_MES,
        LARANJA,
        NEUTRO,
        SALARIO,
        VERDE,
        VERMELHO,
        alt,
        mo,
        pd,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Salário mínimo × cesta básica

    Quanto do salário mínimo a cesta básica consome?

    - **Cesta:** `data/processed/cesta-basica-br/`, gerada por `notebooks/01_cesta_basica_merge.py`.
    - **Salário mínimo:** `data/raw/salario-minimo/salario-minimo_nominal_e_real.csv`, com o
      valor nominal e o valor real (R$ do último mês).

    Os dois valores nominais já vêm convertidos para reais em todas as épocas pelo mesmo fator.
    Por isso a razão **cesta ÷ salário** não depende da moeda.
    """)
    return


@app.cell
def _(CESTA, SALARIO, mo, pd):
    mo.stop(
        not CESTA.exists(),
        mo.md("⚠️ Rode antes `notebooks/01_cesta_basica_merge.py` para gerar a cesta deduplicada."),
    )
    cesta = pd.read_parquet(CESTA)
    salario = pd.read_csv(SALARIO, encoding="utf-8-sig")
    return cesta, salario


@app.cell
def _(HORAS_MES, cesta, pd, salario):
    df = cesta.merge(salario, on="data", how="left", validate="m:1")
    assert df["nominal_rs"].notna().all(), "mês de cesta sem salário mínimo"

    df["mes"] = pd.to_datetime(df["data"])
    df["capital"] = df["municipio"] + " (" + df["uf"] + ")"
    df["pct_salario"] = df["valor_rs"] / df["nominal_rs"] * 100
    df["horas_trabalho"] = df["pct_salario"] / 100 * HORAS_MES
    # Poder de compra: quantas cestas um salário mínimo compra (independe de moeda/deflator)
    df["cestas_por_sm"] = df["nominal_rs"] / df["valor_rs"]
    # Mesmo deflator do salário real (R$ do último mês) aplicado à cesta
    df["cesta_real_rs"] = df["valor_rs"] * df["real_rs_ultimo_mes"] / df["nominal_rs"]
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ultimo = df["data"].max()
    _u = df[df["data"] == ultimo]
    _sp = _u[_u["uf"] == "SP"].iloc[0]
    _barata, _cara = _u.nsmallest(1, "pct_salario").iloc[0], _u.nlargest(1, "pct_salario").iloc[0]

    def _stat(rotulo, valor, sub):
        return mo.stat(value=valor, label=rotulo, caption=sub, bordered=True)

    mo.vstack(
        [
            mo.md(f"## Retrato de {ultimo}"),
            mo.hstack(
                [
                    _stat("Salário mínimo", f"R$ {_sp['nominal_rs']:,.0f}", "nominal"),
                    _stat(
                        "Poder de compra",
                        f"{_sp['cestas_por_sm']:.2f} cestas",
                        "por salário mínimo em São Paulo",
                    ),
                    _stat(
                        "Cesta mais cara", f"{_cara['pct_salario']:.0f}% do SM", _cara["capital"]
                    ),
                    _stat(
                        "Cesta mais barata",
                        f"{_barata['pct_salario']:.0f}% do SM",
                        _barata["capital"],
                    ),
                    _stat(
                        "Mediana das capitais",
                        f"{_u['pct_salario'].median():.0f}% do SM",
                        f"≈ {_u['horas_trabalho'].median():.0f} h de trabalho",
                    ),
                ],
                widths="equal",
            ),
        ]
    )
    """)
    return


@app.cell
def _(alt, pd):
    def linha_com_hover(base, cor_enc, tooltip, titulo):
        """Linhas finas + crosshair vertical com tooltip no mês mais próximo."""
        _hover = alt.selection_point(
            fields=["mes"], nearest=True, on="pointerover", empty=False, clear="pointerout"
        )
        _linhas = base.mark_line(strokeWidth=2).encode(color=cor_enc)
        _pontos = (
            base.mark_point(size=80, filled=True, stroke="white", strokeWidth=2)
            .encode(color=cor_enc, opacity=alt.condition(_hover, alt.value(1), alt.value(0)))
            .add_params(_hover)
        )
        _regua = (
            base.mark_rule(color="#898781", strokeWidth=1)
            .encode(opacity=alt.condition(_hover, alt.value(0.6), alt.value(0)), tooltip=tooltip)
            .transform_filter(_hover)
        )
        return (_linhas + _pontos + _regua).properties(title=titulo, width="container", height=320)

    def marco_plano_real():
        """Linha vertical + rótulo em 1994-07, quando o real entrou em circulação."""
        # Dados próprios (1 linha): sem isso a camada herda o dataset do gráfico
        # e desenha o rótulo uma vez por linha.
        _marco = alt.Chart(
            pd.DataFrame({"mes": [pd.Timestamp("1994-07-01")], "rotulo": ["Plano Real (jul/1994)"]})
        ).encode(x="mes:T")
        _linha = _marco.mark_rule(color="#52514e", strokeWidth=1, strokeDash=[2, 3])
        _rotulo = _marco.mark_text(
            align="right", baseline="top", dx=-4, dy=4, color="#52514e", fontSize=11
        ).encode(y=alt.value(0), text="rotulo:N")
        return _linha + _rotulo

    return linha_com_hover, marco_plano_real


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. São Paulo, 1959 → hoje

    São Paulo é a única capital com série completa, então dá a visão de longo prazo.
    A linha pontilhada marca **100%**: acima dela, uma cesta custava mais que
    o salário mínimo inteiro.

    O painel de baixo mostra o **poder de compra**: quantas cestas um salário mínimo compra.
    Abaixo de **1 cesta**, o salário não pagava nem uma.
    """)
    return


@app.cell
def _(AZUL, VERDE, alt, df, linha_com_hover, marco_plano_real, mo):
    sp = df[df["uf"] == "SP"].copy()
    _base = alt.Chart(sp).encode(
        x=alt.X("mes:T", title=None),
        y=alt.Y("pct_salario:Q", title="Cesta em % do salário mínimo"),
    )
    _tooltip = [
        alt.Tooltip("data:N", title="Mês"),
        alt.Tooltip("pct_salario:Q", title="% do SM", format=".1f"),
        alt.Tooltip("horas_trabalho:Q", title="Horas de trabalho", format=".0f"),
        alt.Tooltip("valor_rs:Q", title="Cesta (R$ nominal)", format=",.2f"),
    ]
    _cem = alt.Chart().mark_rule(strokeDash=[4, 4], color="#898781").encode(y=alt.datum(100))
    _custo = (
        linha_com_hover(
            _base, alt.value(AZUL), _tooltip, "São Paulo: custo da cesta em % do salário mínimo"
        )
        + _cem
        + marco_plano_real()
    )

    _base_pc = alt.Chart(sp).encode(
        x=alt.X("mes:T", title=None),
        y=alt.Y("cestas_por_sm:Q", title="Cestas por salário mínimo"),
    )
    _tooltip_pc = [
        alt.Tooltip("data:N", title="Mês"),
        alt.Tooltip("cestas_por_sm:Q", title="Cestas por SM", format=".2f"),
        alt.Tooltip("nominal_rs:Q", title="SM (R$ nominal)", format=",.2f"),
        alt.Tooltip("valor_rs:Q", title="Cesta (R$ nominal)", format=",.2f"),
    ]
    _uma = alt.Chart().mark_rule(strokeDash=[4, 4], color="#898781").encode(y=alt.datum(1))
    _poder = (
        linha_com_hover(
            _base_pc,
            alt.value(VERDE),
            _tooltip_pc,
            "São Paulo: poder de compra (cestas por salário mínimo)",
        ).properties(height=240)
        + _uma
        + marco_plano_real()
    )
    mo.vstack([_custo, _poder])
    return (sp,)


@app.cell
def _(mo, sp):
    _pico = sp.loc[sp["pct_salario"].idxmax()]
    _vale = sp.loc[sp["pct_salario"].idxmin()]
    _acima = sp[sp["pct_salario"] > 100]
    _pc_max = sp.loc[sp["cestas_por_sm"].idxmax()]
    _pc_hoje = sp.iloc[-1]
    mo.md(
        f"- **Pico:** {_pico['data']}, quando a cesta custava "
        f"**{_pico['pct_salario']:.0f}%** do SM "
        f"(≈ {_pico['horas_trabalho']:.0f} h de trabalho).\n"
        f"- **Mínimo:** {_vale['data']}, com **{_vale['pct_salario']:.0f}%**.\n"
        f"- A cesta passou do salário inteiro em **{len(_acima)} meses**, entre "
        f"{_acima['data'].min()} e {_acima['data'].max()}.\n"
        f"- **Maior poder de compra:** {_pc_max['data']}, com "
        f"**{_pc_max['cestas_por_sm']:.2f} cestas** por SM. Em {_pc_hoje['data']}: "
        f"**{_pc_hoje['cestas_por_sm']:.2f}**."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Valores reais em São Paulo

    Salário mínimo e cesta corrigidos pelo **mesmo deflator** da série real do salário
    (em R$ do último mês disponível). As duas curvas ficam na mesma unidade e podem dividir um eixo.
    A **faixa sombreada** é o que sobra do salário depois de comprar a cesta.
    """)
    return


@app.cell
def _(AZUL, LARANJA, alt, linha_com_hover, marco_plano_real, sp):
    _real = sp.melt(
        id_vars=["mes", "data"],
        value_vars=["real_rs_ultimo_mes", "cesta_real_rs"],
        var_name="serie",
        value_name="rs",
    )
    _real["serie"] = _real["serie"].map(
        {"real_rs_ultimo_mes": "Salário mínimo", "cesta_real_rs": "Cesta básica"}
    )
    _cor = alt.Color(
        "serie:N",
        title=None,
        scale=alt.Scale(domain=["Salário mínimo", "Cesta básica"], range=[AZUL, LARANJA]),
        legend=alt.Legend(orient="top"),
    )
    _base = alt.Chart(_real).encode(
        x=alt.X("mes:T", title=None),
        y=alt.Y("rs:Q", title="R$ do último mês"),
    )
    _tooltip = [
        alt.Tooltip("data:N", title="Mês"),
        alt.Tooltip("serie:N", title="Série"),
        alt.Tooltip("rs:Q", title="R$ real", format=",.0f"),
    ]
    # Faixa entre as curvas = o que sobra do salário depois da cesta (poder de compra)
    _faixa = (
        alt.Chart(sp)
        .mark_area(color=AZUL, opacity=0.12)
        .encode(x="mes:T", y="cesta_real_rs:Q", y2="real_rs_ultimo_mes:Q")
    )
    (
        _faixa
        + linha_com_hover(
            _base, _cor, _tooltip, "São Paulo: salário mínimo e cesta em valores reais"
        )
        + marco_plano_real()
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Delta: salário mínimo real − cesta real (São Paulo)

    Quanto sobra do salário depois de comprar a cesta, em R$ do último mês.
    **Azul** é sobra e **vermelho** é déficit (a cesta custou mais que o salário).
    Com mais de 800 meses, os dois gráficos agregam por ano.
    O gráfico de linha tem um **segundo eixo (direita, verde tracejado)** com o poder de compra
    em cestas por salário mínimo. Os dois eixos têm escalas independentes: compare as
    tendências das duas linhas, não a altura de uma contra a outra.
    """)
    return


@app.cell
def _(pd, sp):
    _d = sp.assign(
        delta_rs=sp["real_rs_ultimo_mes"] - sp["cesta_real_rs"],
        ano=sp["mes"].dt.year,
    )
    delta_mensal = _d[["mes", "data", "ano", "delta_rs", "cestas_por_sm"]]
    delta_anual = (
        delta_mensal.groupby("ano")
        .agg(
            media=("delta_rs", "mean"),
            dp=("delta_rs", "std"),
            n=("delta_rs", "size"),
            cestas_sm=("cestas_por_sm", "mean"),
        )
        .reset_index()
    )
    # IC de 95% da média anual (aprox. normal); ano com 1 mês fica sem faixa
    _erro = 1.96 * delta_anual["dp"] / delta_anual["n"] ** 0.5
    delta_anual["ic_inf"] = delta_anual["media"] - _erro
    delta_anual["ic_sup"] = delta_anual["media"] + _erro
    delta_anual["mes"] = pd.to_datetime(delta_anual["ano"].astype(str) + "-07-01")
    delta_anual["sinal"] = delta_anual["media"].ge(0).map({True: "Sobra", False: "Déficit"})
    return delta_anual, delta_mensal


@app.cell
def _(AZUL, VERMELHO, alt, delta_anual, marco_plano_real):
    _barras = (
        alt.Chart(delta_anual)
        .mark_bar(cornerRadiusEnd=4, width={"band": 0.75})
        .encode(
            x=alt.X("year(mes):T", title=None),
            y=alt.Y("media:Q", title="Delta médio no ano (R$ do último mês)"),
            color=alt.Color(
                "sinal:N",
                title=None,
                scale=alt.Scale(domain=["Sobra", "Déficit"], range=[AZUL, VERMELHO]),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("media:Q", title="Delta médio (R$)", format=",.0f"),
                alt.Tooltip("n:Q", title="Meses"),
            ],
        )
    )
    _zero = alt.Chart().mark_rule(color="#52514e", strokeWidth=1).encode(y=alt.datum(0))
    (_barras + _zero + marco_plano_real()).properties(
        title="São Paulo: salário mínimo real − cesta real, média anual",
        width="container",
        height=320,
    )
    return


@app.cell
def _(
    AZUL,
    NEUTRO,
    VERDE,
    alt,
    delta_anual,
    delta_mensal,
    linha_com_hover,
    marco_plano_real,
):
    _x = alt.X("mes:T", title=None)
    _pontos = (
        alt.Chart(delta_mensal)
        .mark_circle(size=14, color=NEUTRO, opacity=0.45)
        .encode(
            x=_x,
            y=alt.Y("delta_rs:Q", title="Delta (R$ do último mês)"),
            tooltip=[
                alt.Tooltip("data:N", title="Mês"),
                alt.Tooltip("delta_rs:Q", title="Delta (R$)", format=",.0f"),
            ],
        )
    )
    _faixa = (
        alt.Chart(delta_anual)
        .mark_area(color=AZUL, opacity=0.2)
        .encode(x=_x, y="ic_inf:Q", y2="ic_sup:Q")
    )
    _linha = linha_com_hover(
        alt.Chart(delta_anual).encode(x=_x, y="media:Q"),
        alt.value(AZUL),
        [
            alt.Tooltip("ano:O", title="Ano"),
            alt.Tooltip("media:Q", title="Média (R$)", format=",.0f"),
            alt.Tooltip("ic_inf:Q", title="IC 95% inf.", format=",.0f"),
            alt.Tooltip("ic_sup:Q", title="IC 95% sup.", format=",.0f"),
            alt.Tooltip("cestas_sm:Q", title="Cestas por SM", format=".2f"),
            alt.Tooltip("n:Q", title="Meses"),
        ],
        "São Paulo: delta (R$, eixo esquerdo) e poder de compra (cestas por SM, eixo direito)",
    )
    _zero = alt.Chart().mark_rule(color="#52514e", strokeWidth=1).encode(y=alt.datum(0))
    _delta = _pontos + _faixa + _zero + _linha + marco_plano_real()

    # Segundo eixo Y (direita): poder de compra, média anual de cestas por SM
    _poder = (
        alt.Chart(delta_anual)
        .mark_line(color=VERDE, strokeWidth=2, strokeDash=[6, 3])
        .encode(
            x=_x,
            y=alt.Y(
                "cestas_sm:Q",
                title="Poder de compra (cestas por SM)",
                axis=alt.Axis(orient="right", titleColor=VERDE, grid=False),
            ),
        )
    )
    _legenda = (
        alt.Chart(
            alt.Data(
                values=[
                    {"serie": "Delta médio anual (R$)"},
                    {"serie": "Poder de compra (cestas por SM)"},
                ]
            )
        )
        .mark_line(strokeWidth=2)
        .encode(
            color=alt.Color(
                "serie:N",
                title=None,
                scale=alt.Scale(
                    domain=["Delta médio anual (R$)", "Poder de compra (cestas por SM)"],
                    range=[AZUL, VERDE],
                ),
                legend=alt.Legend(orient="top"),
            ),
            strokeDash=alt.StrokeDash(
                "serie:N",
                scale=alt.Scale(
                    domain=["Delta médio anual (R$)", "Poder de compra (cestas por SM)"],
                    range=[[1, 0], [6, 3]],
                ),
                legend=None,
            ),
        )
    )
    alt.layer(_delta + _legenda, _poder).resolve_scale(y="independent")
    return


@app.cell
def _(delta_anual, delta_mensal, mo):
    _deficit = delta_anual[delta_anual["media"] < 0]
    _melhor = delta_anual.loc[delta_anual["media"].idxmax()]
    _ultimo = delta_mensal.iloc[-1]
    mo.md(
        f"- **{len(_deficit)} anos** com déficit médio: "
        f"{', '.join(map(str, _deficit['ano']))}.\n"
        f"- **Maior sobra média:** {_melhor['ano']}, com **R$ {_melhor['media']:,.0f}**.\n"
        f"- **{_ultimo['data']}:** sobram **R$ {_ultimo['delta_rs']:,.0f}** depois da cesta."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. As 27 capitais no último mês
    """)
    return


@app.cell
def _(AZUL, alt, df):
    ultimo = df["data"].max()
    _u = df[df["data"] == ultimo]
    _barras = (
        alt.Chart(_u)
        .mark_bar(color=AZUL, cornerRadiusEnd=4, height={"band": 0.75})
        .encode(
            x=alt.X("pct_salario:Q", title="Cesta em % do salário mínimo"),
            y=alt.Y("capital:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("capital:N", title="Capital"),
                alt.Tooltip("valor_rs:Q", title="Cesta (R$)", format=",.2f"),
                alt.Tooltip("pct_salario:Q", title="% do SM", format=".1f"),
                alt.Tooltip("horas_trabalho:Q", title="Horas de trabalho", format=".0f"),
            ],
        )
    )
    _rotulos = _barras.mark_text(align="left", dx=4, color="#52514e", fontSize=11).encode(
        text=alt.Text("pct_salario:Q", format=".0f")
    )
    (_barras + _rotulos).properties(
        title=f"Cesta em % do salário mínimo por capital ({ultimo})", width="container", height=560
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Top 10 capitais com a cesta mais cara, 2004 → 2026

    Um painel por capital, em ordem do ranking. Cada barra é a **média anual do custo da
    cesta em % do salário mínimo**. Todos os painéis têm o **mesmo eixo Y**, então a altura
    das barras pode ser comparada entre capitais. A linha cinza é a mediana das 10 no ano:
    barra acima dela significa uma cesta mais pesada que a da capital típica do grupo.

    Ranking pela média do período, só com capitais que têm dado em **todos os anos**.
    Capitais com lacunas ficam de fora para não distorcer a média.
    """)
    return


@app.cell
def _(df):
    ANO_INI, TOP_N = 2004, 10
    _p = df[df["mes"].dt.year >= ANO_INI].assign(ano=lambda d: d["mes"].dt.year)
    anual_cap = (
        _p.groupby(["capital", "ano"])
        .agg(
            pct=("pct_salario", "mean"),
            cesta_rs=("valor_rs", "mean"),
            horas=("horas_trabalho", "mean"),
            cestas_sm=("cestas_por_sm", "mean"),
            meses=("data", "size"),
        )
        .reset_index()
    )
    # Posição de cada capital no ano, entre todas as capitais com dado naquele ano
    anual_cap["posicao"] = anual_cap.groupby("ano")["pct"].rank(ascending=False).astype(int)
    anual_cap["n_capitais"] = anual_cap.groupby("ano")["capital"].transform("size")

    _n_anos = anual_cap["ano"].nunique()
    _resumo = anual_cap.groupby("capital").agg(anos=("ano", "size"), media=("pct", "mean"))
    excluidas = _resumo[_resumo["anos"] < _n_anos].index.tolist()
    top10 = _resumo[_resumo["anos"] == _n_anos].nlargest(TOP_N, "media").index.tolist()
    return ANO_INI, anual_cap, excluidas, top10


@app.cell
def _(ANO_INI, AZUL, NEUTRO, alt, anual_cap, top10):
    _h = anual_cap[anual_cap["capital"].isin(top10)].copy()
    # Referência comum a todos os painéis: mediana das 10 capitais em cada ano
    _h["mediana_top10"] = _h.groupby("ano")["pct"].transform("median")

    _x = alt.X(
        "ano:O",
        title=None,
        axis=alt.Axis(labelAngle=0, labelExpr="datum.value % 4 == 0 ? datum.label : ''"),
    )
    _barras = (
        alt.Chart()
        .mark_bar(color=AZUL, cornerRadiusEnd=3)
        .encode(
            x=_x,
            y=alt.Y("pct:Q", title="% do SM"),
            tooltip=[
                alt.Tooltip("capital:N", title="Capital"),
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("pct:Q", title="Cesta em % do SM", format=".1f"),
                alt.Tooltip("mediana_top10:Q", title="Mediana das 10", format=".1f"),
                alt.Tooltip("cesta_rs:Q", title="Cesta média (R$)", format=",.2f"),
                alt.Tooltip("cestas_sm:Q", title="Cestas por SM", format=".2f"),
                alt.Tooltip("horas:Q", title="Horas de trabalho", format=".0f"),
                alt.Tooltip("posicao:Q", title="Posição no ano"),
                alt.Tooltip("n_capitais:Q", title="Capitais com dado"),
            ],
        )
    )
    _mediana = (
        alt.Chart()
        .mark_line(color=NEUTRO, strokeWidth=2, interpolate="step")
        .encode(x=_x, y="mediana_top10:Q")
    )
    (
        alt.layer(_barras, _mediana, data=_h)
        .properties(width=380, height=130)
        .facet(
            facet=alt.Facet(
                "capital:N",
                sort=top10,
                title=None,
                header=alt.Header(labelFontSize=12, labelFontWeight="bold", labelAnchor="start"),
            ),
            columns=2,
        )
        .resolve_axis(x="independent")
        .properties(
            title=alt.Title(
                f"Top 10 capitais: cesta em % do salário mínimo, média anual ({ANO_INI}–2026)",
                subtitle="Barras: a capital · linha cinza: mediana das 10 capitais no ano",
            )
        )
    )
    return


@app.cell
def _(anual_cap, excluidas, mo, top10):
    _h = anual_cap[anual_cap["capital"].isin(top10)]
    _pico = _h.loc[_h["pct"].idxmax()]
    _vale = _h.loc[_h["pct"].idxmin()]
    _primeiro = _h[_h["posicao"] == 1].groupby("capital").size().sort_values(ascending=False)
    mo.md(
        f"- **Mais pesada:** {_pico['capital']} em {_pico['ano']}, "
        f"com **{_pico['pct']:.1f}%** do SM.\n"
        f"- **Mais leve:** {_vale['capital']} em {_vale['ano']}, "
        f"com **{_vale['pct']:.1f}%**.\n"
        f"- **1º lugar no ano:** "
        + ", ".join(f"{c} ({n} anos)" for c, n in _primeiro.items())
        + ".\n"
        f"- Fora do ranking por lacunas na série: {', '.join(excluidas)}."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Comparar uma capital com as demais

    A série com todas as capitais começa em 2015-12. A mediana usa as capitais com dado em cada mês,
    porque alguns meses têm cobertura parcial.
    """)
    return


@app.cell
def _(df, mo):
    _opcoes = sorted(df.loc[df["data"] >= "2015-12", "capital"].unique())
    escolha = mo.ui.dropdown(_opcoes, value="São Paulo (SP)", label="Capital")
    escolha
    return (escolha,)


@app.cell
def _(AZUL, NEUTRO, alt, df, escolha, linha_com_hover, pd):
    _recente = df[df["data"] >= "2015-12"]
    _mediana = (
        _recente.groupby(["mes", "data"], as_index=False)["pct_salario"]
        .median()
        .assign(serie="Mediana das capitais")
    )
    _cap = _recente.loc[_recente["capital"] == escolha.value, ["mes", "data", "pct_salario"]]
    _comp = pd.concat([_cap.assign(serie=escolha.value), _mediana])
    _cor = alt.Color(
        "serie:N",
        title=None,
        scale=alt.Scale(domain=[escolha.value, "Mediana das capitais"], range=[AZUL, NEUTRO]),
        legend=alt.Legend(orient="top"),
    )
    _base = alt.Chart(_comp).encode(
        x=alt.X("mes:T", title=None),
        y=alt.Y("pct_salario:Q", title="Cesta em % do salário mínimo"),
    )
    _tooltip = [
        alt.Tooltip("data:N", title="Mês"),
        alt.Tooltip("serie:N", title="Série"),
        alt.Tooltip("pct_salario:Q", title="% do SM", format=".1f"),
    ]
    linha_com_hover(_base, _cor, _tooltip, f"{escolha.value} × mediana das capitais")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Tabela: média anual (% do salário mínimo)
    """)
    return


@app.cell
def _(df, mo):
    _t = (
        df[df["data"] >= "2016-01"]
        .assign(ano=lambda d: d["data"].str[:4])
        .pivot_table(index="capital", columns="ano", values="pct_salario", aggfunc="mean")
        .round(1)
    )
    _t = _t.sort_values(_t.columns[-1], ascending=False).reset_index()
    mo.ui.table(_t, page_size=27, selection=None)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 8. O "serrote" entre reajustes (São Paulo, 1995 → 2026)

    Entre um reajuste e o seguinte o salário fica parado e a cesta continua mudando de preço,
    então o poder de compra cai aos poucos até o próximo reajuste. Cada linha é um ciclo, que
    começa no mês do reajuste (= 100). Ciclos com menos de 6 meses (correções extras de
    2011, 2020 e 2023) ficam de fora.
    """)
    return


@app.cell
def _(pd, sp):
    _s = sp.sort_values("mes").copy()
    _s["reajuste"] = _s["nominal_rs"].ne(_s["nominal_rs"].shift())
    _s["ciclo"] = _s["reajuste"].cumsum()
    _s = _s[_s["mes"] >= "1995-05-01"]
    _s["meses_desde"] = _s.groupby("ciclo").cumcount()
    _inicio = _s.groupby("ciclo")["data"].transform("first")
    _base = _s.groupby("ciclo")["cestas_por_sm"].transform("first")
    _s["indice"] = _s["cestas_por_sm"] / _base * 100
    _s["ciclo_rot"] = "Reajuste de " + _inicio
    _tam = _s.groupby("ciclo")["meses_desde"].transform("size")
    _ultimo_ciclo = _s["ciclo"].max()
    _s = _s[(_tam >= 6) | (_s["ciclo"] == _ultimo_ciclo)]

    ciclo_atual = _s.loc[_s["ciclo"] == _ultimo_ciclo, "ciclo_rot"].iloc[0]
    _s["grupo"] = (
        _s["ciclo"]
        .eq(_ultimo_ciclo)
        .map({True: f"Ciclo atual ({ciclo_atual[-7:]})", False: "Demais ciclos"})
    )
    _anteriores = _s[_s["ciclo"] != _ultimo_ciclo]
    _med = (
        _anteriores.groupby("meses_desde", as_index=False)
        .agg(indice=("indice", "median"), n_ciclos=("ciclo", "nunique"))
        .assign(ciclo_rot="Mediana dos ciclos", grupo="Mediana dos ciclos")
    )
    # Só onde pelo menos metade dos ciclos chegou: no fim, poucos ciclos distorcem a mediana
    _med = _med[_med["n_ciclos"] >= _anteriores["ciclo"].nunique() / 2]
    serrote = pd.concat(
        [_s[["meses_desde", "indice", "ciclo_rot", "grupo", "data"]], _med], ignore_index=True
    )
    return ciclo_atual, serrote


@app.cell
def _(AZUL, LARANJA, alt, ciclo_atual, serrote):
    _dom = ["Mediana dos ciclos", f"Ciclo atual ({ciclo_atual[-7:]})", "Demais ciclos"]
    _cor = alt.Color(
        "grupo:N",
        title=None,
        scale=alt.Scale(domain=_dom, range=[AZUL, LARANJA, "#c3c2b7"]),
        legend=alt.Legend(orient="top"),
    )
    _linhas = (
        alt.Chart(serrote)
        .mark_line(clip=True)
        .encode(
            x=alt.X(
                "meses_desde:Q",
                title="Meses desde o reajuste",
                scale=alt.Scale(domain=[0, 11]),
                axis=alt.Axis(tickMinStep=1),
            ),
            y=alt.Y(
                "indice:Q",
                title="Poder de compra (mês do reajuste = 100)",
                scale=alt.Scale(zero=False),
            ),
            color=_cor,
            detail="ciclo_rot:N",
            strokeWidth=alt.condition(
                alt.datum.grupo == "Demais ciclos", alt.value(1), alt.value(3)
            ),
            order=alt.Order("grupo:N", sort="descending"),
            tooltip=[
                alt.Tooltip("ciclo_rot:N", title="Ciclo"),
                alt.Tooltip("meses_desde:Q", title="Meses desde o reajuste"),
                alt.Tooltip("indice:Q", title="Poder de compra", format=".1f"),
            ],
        )
    )
    _cem = alt.Chart().mark_rule(color="#52514e", strokeDash=[4, 4]).encode(y=alt.datum(100))
    (_linhas + _cem).properties(
        title="São Paulo: poder de compra ao longo de cada ciclo de reajuste",
        width="container",
        height=340,
    )
    return


@app.cell
def _(mo, serrote):
    _med = serrote[serrote["grupo"] == "Mediana dos ciclos"].set_index("meses_desde")["indice"]
    _fim = _med[_med.index <= 11]
    mo.md(
        f"- Na mediana, o poder de compra chega ao **mês {_fim.index.max()}** do ciclo em "
        f"**{_fim.iloc[-1]:.1f}** (variação de **{_fim.iloc[-1] - 100:+.1f}%** desde o reajuste).\n"
        f"- O pior mês da mediana é o **{_fim.idxmin()}**, com **{_fim.min():.1f}**."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 9. A diferença entre capitais ao longo do tempo (2015-12 → 2026)

    A faixa vai da capital com a cesta mais barata até a mais cara em cada mês (em % do
    salário mínimo) e a linha é a mediana. A área cinza marca os meses com **cobertura
    parcial**: menos capitais pesquisadas, então parte do estreitamento da faixa ali vem
    só de haver menos capitais.
    """)
    return


@app.cell
def _(df, pd):
    _r = df[df["data"] >= "2015-12"]
    _ext = _r.loc[_r.groupby("mes")["pct_salario"].idxmin(), ["mes", "capital"]].rename(
        columns={"capital": "mais_barata"}
    )
    _ext2 = _r.loc[_r.groupby("mes")["pct_salario"].idxmax(), ["mes", "capital"]].rename(
        columns={"capital": "mais_cara"}
    )
    faixa_cap = (
        _r.groupby("mes")
        .agg(
            data=("data", "first"),
            minimo=("pct_salario", "min"),
            mediana=("pct_salario", "median"),
            maximo=("pct_salario", "max"),
            n=("capital", "size"),
        )
        .reset_index()
        .merge(_ext, on="mes")
        .merge(_ext2, on="mes")
    )
    faixa_cap["amplitude"] = faixa_cap["maximo"] - faixa_cap["minimo"]

    # Trechos contínuos com menos de 27 capitais
    _parcial = faixa_cap["n"] < 27
    _bloco = _parcial.ne(_parcial.shift()).cumsum()
    cobertura_parcial = (
        faixa_cap[_parcial]
        .groupby(_bloco[_parcial])
        .agg(inicio=("mes", "first"), fim=("mes", "last"), n_min=("n", "min"))
        .reset_index(drop=True)
    )
    cobertura_parcial["fim"] = cobertura_parcial["fim"] + pd.offsets.MonthEnd(1)
    return cobertura_parcial, faixa_cap


@app.cell
def _(AZUL, alt, cobertura_parcial, faixa_cap, linha_com_hover):
    _x = alt.X("mes:T", title=None)
    _sombra = (
        alt.Chart(cobertura_parcial)
        .mark_rect(color="#c3c2b7", opacity=0.3)
        .encode(x="inicio:T", x2="fim:T")
    )
    _sombra_rot = (
        alt.Chart(cobertura_parcial)
        .mark_text(align="left", baseline="top", dx=4, dy=4, color="#52514e", fontSize=11)
        .encode(x="inicio:T", y=alt.value(0), text=alt.value("cobertura parcial"))
    )
    _faixa = (
        alt.Chart(faixa_cap)
        .mark_area(color=AZUL, opacity=0.2)
        .encode(x=_x, y=alt.Y("minimo:Q", title="Cesta em % do salário mínimo"), y2="maximo:Q")
    )
    _linha = linha_com_hover(
        alt.Chart(faixa_cap).encode(x=_x, y="mediana:Q"),
        alt.value(AZUL),
        [
            alt.Tooltip("data:N", title="Mês"),
            alt.Tooltip("maximo:Q", title="Mais cara (%)", format=".1f"),
            alt.Tooltip("mais_cara:N", title="Capital mais cara"),
            alt.Tooltip("mediana:Q", title="Mediana (%)", format=".1f"),
            alt.Tooltip("minimo:Q", title="Mais barata (%)", format=".1f"),
            alt.Tooltip("mais_barata:N", title="Capital mais barata"),
            alt.Tooltip("amplitude:Q", title="Diferença (p.p.)", format=".1f"),
            alt.Tooltip("n:Q", title="Capitais com dado"),
        ],
        "Cesta em % do SM: faixa da mais barata à mais cara, e mediana das capitais",
    )
    _sombra + _sombra_rot + _faixa + _linha
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 10. 2004 × 2026: quem mudou de posição

    Ranking das 16 capitais com dado nos dois anos: **1º = cesta mais pesada** em relação
    ao salário mínimo (média anual). Vermelho: a capital subiu no ranking (ficou
    relativamente mais pesada). Azul: desceu (relativamente mais leve).
    """)
    return


@app.cell
def _(df):
    _a = df[df["mes"].dt.year.isin([2004, 2026])].assign(ano=lambda d: d["mes"].dt.year)
    _m = _a.groupby(["capital", "ano"])["pct_salario"].mean().unstack().dropna()
    _m["pos_2004"] = _m[2004].rank(ascending=False).astype(int)
    _m["pos_2026"] = _m[2026].rank(ascending=False).astype(int)
    _m["mudanca"] = _m["pos_2004"] - _m["pos_2026"]
    _m["sentido"] = "Manteve a posição"
    _m.loc[_m["mudanca"] > 0, "sentido"] = "Subiu (relativamente mais pesada)"
    _m.loc[_m["mudanca"] < 0, "sentido"] = "Desceu (relativamente mais leve)"
    _m = _m.reset_index()
    slope = _m.melt(
        id_vars=["capital", "sentido", "mudanca", 2004, 2026],
        value_vars=["pos_2004", "pos_2026"],
        var_name="ano",
        value_name="posicao",
    )
    slope["ano"] = slope["ano"].str[-4:]
    slope["pct"] = slope.apply(lambda r: r[int(r["ano"])], axis=1)
    slope["rotulo_esq"] = slope["capital"] + "  " + slope["pct"].map("{:.0f}%".format)
    slope["rotulo_dir"] = slope["pct"].map("{:.0f}%".format) + "  " + slope["capital"]
    slope = slope.drop(columns=[2004, 2026])
    return (slope,)


@app.cell
def _(AZUL, NEUTRO, VERMELHO, alt, slope):
    _dom = [
        "Subiu (relativamente mais pesada)",
        "Desceu (relativamente mais leve)",
        "Manteve a posição",
    ]
    _enc = dict(
        x=alt.X(
            "ano:O",
            title=None,
            axis=alt.Axis(orient="top", labelAngle=0, labelFontSize=13, labelFontWeight="bold"),
            scale=alt.Scale(padding=0.05),
        ),
        y=alt.Y("posicao:O", title=None, axis=None),
        color=alt.Color(
            "sentido:N",
            title=None,
            scale=alt.Scale(domain=_dom, range=[VERMELHO, AZUL, NEUTRO]),
            legend=alt.Legend(orient="bottom"),
        ),
    )
    _tooltip = [
        alt.Tooltip("capital:N", title="Capital"),
        alt.Tooltip("ano:N", title="Ano"),
        alt.Tooltip("posicao:Q", title="Posição"),
        alt.Tooltip("pct:Q", title="% do SM", format=".1f"),
        alt.Tooltip("mudanca:Q", title="Posições ganhas"),
    ]
    _base = alt.Chart(slope).encode(**_enc)
    _linhas = _base.mark_line(strokeWidth=2).encode(detail="capital:N", tooltip=_tooltip)
    _pontos = _base.mark_circle(size=90, stroke="white", strokeWidth=2, opacity=1).encode(
        tooltip=_tooltip
    )
    _esq = (
        _base.transform_filter(alt.datum.ano == "2004")
        .mark_text(align="right", dx=-10, fontSize=11, color="#0b0b0b")
        .encode(text="rotulo_esq:N", color=alt.value("#0b0b0b"))
    )
    _dir = (
        _base.transform_filter(alt.datum.ano == "2026")
        .mark_text(align="left", dx=10, fontSize=11, color="#0b0b0b")
        .encode(text="rotulo_dir:N", color=alt.value("#0b0b0b"))
    )
    (_linhas + _pontos + _esq + _dir).properties(
        title="Ranking da cesta em % do salário mínimo: 2004 × 2026",
        width=260,
        height=16 * 26,
        padding={"left": 190, "right": 190, "top": 10, "bottom": 10},
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 11. Sazonalidade: em que meses a cesta costuma subir?

    Para cada mês do ano, a distribuição da **variação da cesta em relação ao mês anterior**,
    juntando todas as capitais desde 1995 (antes disso a hiperinflação domina tudo).
    A caixa vai do 1º ao 3º quartil e o traço do meio é a mediana. Só entram meses cujo mês
    anterior também tem dado.
    """)
    return


@app.cell
def _(df, pd):
    _d = df[df["data"] >= "1995-01"].sort_values(["capital", "mes"]).copy()
    _ant = _d.groupby("capital")["mes"].shift()
    _contiguo = _ant == _d["mes"] - pd.DateOffset(months=1)
    _d["var_pct"] = _d.groupby("capital")["valor_rs"].pct_change() * 100
    _d = _d[_contiguo]
    _nomes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    _d["mes_ano"] = _d["mes"].dt.month.map(lambda m: _nomes[m - 1])
    sazonal = _d[["capital", "data", "mes_ano", "var_pct"]]
    meses_nomes = _nomes
    return meses_nomes, sazonal


@app.cell
def _(AZUL, alt, meses_nomes, sazonal):
    _caixas = (
        alt.Chart(sazonal)
        .mark_boxplot(
            extent=1.5,
            size=28,
            color=AZUL,
            median=alt.MarkConfig(color="white", strokeWidth=2),
            outliers=alt.MarkConfig(size=6, opacity=0.25, color="#898781"),
            rule=alt.MarkConfig(color="#898781"),
            ticks=False,
        )
        .encode(
            x=alt.X("mes_ano:O", sort=meses_nomes, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "var_pct:Q",
                title="Variação em relação ao mês anterior (%)",
                scale=alt.Scale(domain=[-12, 15], clamp=True),
            ),
        )
    )
    _zero = alt.Chart().mark_rule(color="#52514e").encode(y=alt.datum(0))
    (_caixas + _zero).properties(
        title="Variação mensal da cesta por mês do ano (todas as capitais, 1995–2026)",
        width="container",
        height=340,
    )
    return


@app.cell
def _(meses_nomes, mo, sazonal):
    _m = sazonal.groupby("mes_ano")["var_pct"].median().reindex(meses_nomes)
    mo.md(
        f"- Mediana mais alta: **{_m.idxmax()}** ({_m.max():+.2f}% no mês). "
        f"Mais baixa: **{_m.idxmin()}** ({_m.min():+.2f}%).\n"
        f"- {len(sazonal):,} variações mensais. O eixo vai de −12% a +15%; valores além disso "
        "ficam presos na borda."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 12. Por região (2026)

    Cada ponto é uma capital (média de 2026 da cesta em % do salário mínimo). O traço
    cinza é a mediana da região. Regiões em ordem da mediana.
    """)
    return


@app.cell
def _(df):
    REGIOES = {
        "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
        "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
        "Centro-Oeste": ["DF", "GO", "MS", "MT"],
        "Sudeste": ["ES", "MG", "RJ", "SP"],
        "Sul": ["PR", "RS", "SC"],
    }
    _uf_reg = {uf: reg for reg, ufs in REGIOES.items() for uf in ufs}
    por_regiao = (
        df[df["mes"].dt.year == 2026]
        .groupby(["capital", "uf"], as_index=False)["pct_salario"]
        .mean()
        .assign(regiao=lambda d: d["uf"].map(_uf_reg))
    )
    por_regiao["mediana_reg"] = por_regiao.groupby("regiao")["pct_salario"].transform("median")
    # Posição vertical alternada (0, 1, 2) para pontos próximos não se sobreporem
    por_regiao = por_regiao.sort_values(["regiao", "pct_salario"])
    por_regiao["faixa_y"] = por_regiao.groupby("regiao").cumcount() % 3
    por_regiao["regiao_rot"] = (
        por_regiao["regiao"] + " · mediana " + por_regiao["mediana_reg"].map("{:.1f}%".format)
    )
    ordem_regioes = (
        por_regiao.groupby("regiao_rot")["pct_salario"].median().sort_values(ascending=False).index
    ).tolist()
    return ordem_regioes, por_regiao


@app.cell
def _(AZUL, alt, ordem_regioes, por_regiao):
    _y = alt.Y("regiao_rot:N", sort=ordem_regioes, title=None, scale=alt.Scale(paddingInner=0.15))
    _pontos = (
        alt.Chart(por_regiao)
        .mark_circle(size=140, color=AZUL, opacity=0.85, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X(
                "pct_salario:Q",
                title="Cesta em % do salário mínimo (média de 2026)",
                scale=alt.Scale(zero=False, padding=20),
            ),
            y=_y,
            yOffset=alt.YOffset("faixa_y:O", scale=alt.Scale(paddingOuter=0.6)),
            tooltip=[
                alt.Tooltip("capital:N", title="Capital"),
                alt.Tooltip("regiao:N", title="Região"),
                alt.Tooltip("pct_salario:Q", title="% do SM", format=".1f"),
                alt.Tooltip("mediana_reg:Q", title="Mediana da região", format=".1f"),
            ],
        )
    )
    _med = (
        alt.Chart(por_regiao)
        .mark_tick(color="#52514e", thickness=3, size=34)
        .encode(x="mediana_reg:Q", y=_y)
    )
    (_med + _pontos).properties(
        title="Cesta em % do salário mínimo por região, 2026",
        width="container",
        height=320,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 13. Histograma: horas de trabalho para comprar a cesta em São Paulo, por década

    Cada painel mostra, para uma década, a **parcela dos meses** em cada faixa de horas de
    trabalho (faixas de 20 h, jornada de 220 h/mês). Mesmo eixo horizontal em todos os
    painéis: uma distribuição larga quer dizer que o custo da cesta oscilava muito na década.
    """)
    return


@app.cell
def _(pd, sp):
    _h = sp[["mes", "horas_trabalho"]].copy()
    _h["decada"] = (_h["mes"].dt.year // 10 * 10).astype(str) + "s"
    _bordas = list(range(0, 340, 20))
    _h["faixa"] = pd.cut(_h["horas_trabalho"], bins=_bordas, right=False)
    horas_dec = _h.groupby(["decada", "faixa"], observed=False).size().rename("meses").reset_index()
    horas_dec["parcela"] = horas_dec["meses"] / horas_dec.groupby("decada")["meses"].transform(
        "sum"
    )
    horas_dec["inicio"] = horas_dec["faixa"].map(lambda i: i.left).astype(int)
    horas_dec["fim"] = horas_dec["faixa"].map(lambda i: i.right).astype(int)
    horas_dec = horas_dec.drop(columns="faixa")
    horas_dec = horas_dec[horas_dec["meses"] > 0]
    horas_dec["fim_vis"] = horas_dec["fim"] - 1  # espaço visual entre barras vizinhas
    return (horas_dec,)


@app.cell
def _(AZUL, alt, horas_dec):
    _barras = (
        alt.Chart()
        .mark_bar(color=AZUL, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "inicio:Q",
                title="Horas de trabalho para comprar a cesta",
                scale=alt.Scale(domain=[0, 320]),
                axis=alt.Axis(values=list(range(0, 321, 40))),
            ),
            x2="fim_vis:Q",
            y=alt.Y("parcela:Q", title=None, axis=alt.Axis(format="%", tickCount=2)),
            y2=alt.datum(0),
            tooltip=[
                alt.Tooltip("decada:N", title="Década"),
                alt.Tooltip("inicio:Q", title="De (h)"),
                alt.Tooltip("fim:Q", title="Até (h)"),
                alt.Tooltip("parcela:Q", title="Parcela dos meses", format=".0%"),
                alt.Tooltip("meses:Q", title="Meses"),
            ],
        )
    )
    _jornada = alt.Chart().mark_rule(color="#52514e", strokeDash=[4, 4]).encode(x=alt.datum(220))
    (
        alt.layer(_barras, _jornada, data=horas_dec)
        .properties(width=760, height=70)
        .facet(
            row=alt.Row(
                "decada:N",
                title=None,
                header=alt.Header(labelAngle=0, labelAlign="left", labelFontWeight="bold"),
            )
        )
        .properties(
            title=alt.Title(
                "São Paulo: distribuição das horas de trabalho para comprar a cesta, por década",
                subtitle="Linha tracejada: 220 h = a jornada do mês inteiro",
            )
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 14. Mapa: a cesta em % do salário mínimo em cada capital

    Último mês disponível. Quanto mais escuro o círculo, mais pesada a cesta.
    O contorno do Brasil é carregado da internet (vega-datasets), então o mapa precisa de
    conexão para aparecer.
    """)
    return


@app.cell
def _(df):
    # Coordenadas aproximadas das capitais (latitude, longitude)
    _coords = {
        "AC": (-9.97, -67.81), "AL": (-9.67, -35.74), "AM": (-3.12, -60.02),
        "AP": (0.03, -51.07), "BA": (-12.97, -38.50), "CE": (-3.73, -38.52),
        "DF": (-15.79, -47.88), "ES": (-20.32, -40.34), "GO": (-16.69, -49.26),
        "MA": (-2.53, -44.30), "MG": (-19.92, -43.94), "MS": (-20.47, -54.62),
        "MT": (-15.60, -56.10), "PA": (-1.46, -48.50), "PB": (-7.12, -34.86),
        "PE": (-8.05, -34.88), "PI": (-5.09, -42.80), "PR": (-25.43, -49.27),
        "RJ": (-22.91, -43.17), "RN": (-5.79, -35.21), "RO": (-8.76, -63.90),
        "RR": (2.82, -60.67), "RS": (-30.03, -51.23), "SC": (-27.59, -48.55),
        "SE": (-10.91, -37.07), "SP": (-23.55, -46.63), "TO": (-10.18, -48.33),
    }  # fmt: skip
    _ult = df["data"].max()
    mapa_df = df[df["data"] == _ult][
        ["capital", "uf", "pct_salario", "valor_rs", "horas_trabalho", "data"]
    ].copy()
    mapa_df["lat"] = mapa_df["uf"].map(lambda u: _coords[u][0])
    mapa_df["lon"] = mapa_df["uf"].map(lambda u: _coords[u][1])
    _ext = mapa_df["pct_salario"].isin([mapa_df["pct_salario"].max(), mapa_df["pct_salario"].min()])
    mapa_df["rotulo"] = ""
    mapa_df.loc[_ext, "rotulo"] = (
        mapa_df.loc[_ext, "capital"] + " " + mapa_df.loc[_ext, "pct_salario"].map("{:.0f}%".format)
    )
    return (mapa_df,)


@app.cell
def _(alt, mapa_df):
    _mundo = alt.topo_feature(
        "https://cdn.jsdelivr.net/npm/vega-datasets@2.8.0/data/world-110m.json", "countries"
    )
    _brasil = (
        alt.Chart(_mundo)
        .mark_geoshape(fill="#f0efec", stroke="#c3c2b7", strokeWidth=1)
        .transform_filter(alt.datum.id == 76)
    )
    _geo = dict(latitude="lat:Q", longitude="lon:Q")
    _pontos = (
        alt.Chart(mapa_df)
        .mark_circle(size=260, stroke="white", strokeWidth=1.5, opacity=1)
        .encode(
            **_geo,
            color=alt.Color(
                "pct_salario:Q",
                title="% do SM",
                scale=alt.Scale(range=["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]),
                legend=alt.Legend(orient="top-left"),
            ),
            tooltip=[
                alt.Tooltip("capital:N", title="Capital"),
                alt.Tooltip("pct_salario:Q", title="% do SM", format=".1f"),
                alt.Tooltip("valor_rs:Q", title="Cesta (R$)", format=",.2f"),
                alt.Tooltip("horas_trabalho:Q", title="Horas de trabalho", format=".0f"),
            ],
        )
    )
    _rotulos = (
        alt.Chart(mapa_df[mapa_df["rotulo"] != ""])
        .mark_text(align="left", dx=12, fontSize=12, fontWeight="bold", color="#0b0b0b")
        .encode(**_geo, text="rotulo:N")
    )
    (_brasil + _pontos + _rotulos).project(type="mercator").properties(
        title=f"Cesta em % do salário mínimo por capital ({mapa_df['data'].iloc[0]})",
        width=620,
        height=620,
    )
    return


if __name__ == "__main__":
    app.run()
