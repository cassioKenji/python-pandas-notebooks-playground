import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    from playground import PROCESSED_DIR, RAW_DIR

    SRC = RAW_DIR / "cesta-basica-br"
    OUT = PROCESSED_DIR / "cesta-basica-br"
    KEY = ["data", "codigo_ibge"]
    return KEY, OUT, SRC, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Cesta básica — merge e deduplicação

    Fontes em `data/raw/cesta-basica-br/`:

    | arquivo | formato | conteúdo |
    |---|---|---|
    | `capitais_long.csv` | long | valor em R$ por capital/mês |
    | `capitais_wide.csv` | wide | mesmos dados, uma coluna por capital |
    | `sao-paulo_DIEESE12_CBSP12.csv` | série | SP, **na moeda da época** (= R$ desde 1994-07) |

    Saída: uma tabela long `data, codigo_ibge, uf, municipio, valor_rs, valor_moeda_epoca`.
    """)
    return


@app.cell
def _(SRC, pd):
    long_df = pd.read_csv(SRC / "cesta-basica_capitais_long.csv", encoding="utf-8-sig")
    wide_df = pd.read_csv(SRC / "cesta-basica_capitais_wide.csv", encoding="utf-8-sig")
    sp_df = pd.read_csv(SRC / "cesta-basica_sao-paulo_DIEESE12_CBSP12.csv", encoding="utf-8-sig")
    return long_df, sp_df, wide_df


@app.cell
def _(long_df, wide_df):
    # wide -> long; o código IBGE vem do arquivo long via (uf, municipio)
    _ibge = long_df[["uf", "municipio", "codigo_ibge"]].drop_duplicates()
    _melted = wide_df.melt("data", var_name="coluna", value_name="valor_rs").dropna()
    _melted[["municipio", "uf"]] = _melted["coluna"].str.extract(r"^(.*) \((\w{2})\)$")
    wide_long = _melted.merge(_ibge, on=["uf", "municipio"], how="left", validate="m:1")
    assert wide_long["codigo_ibge"].notna().all(), "capital do wide sem código IBGE"
    wide_long = wide_long[long_df.columns]
    return (wide_long,)


@app.cell
def _(KEY, long_df, mo, pd, wide_long):
    stacked = pd.concat([long_df, wide_long], ignore_index=True)
    capitais = stacked.drop_duplicates()

    # Mesma chave com valores diferentes = conflito real entre as fontes
    _conflitos = capitais[capitais.duplicated(KEY, keep=False)]
    assert _conflitos.empty, _conflitos

    mo.md(
        f"long + wide: **{len(stacked):,}** linhas → **{len(capitais):,}** após remover "
        f"duplicatas exatas ({len(stacked) - len(capitais):,} removidas, 0 conflitos)."
    )
    return (capitais,)


@app.cell
def _(capitais, mo):
    # Séries de cidades diferentes idênticas em todo o período comum = rótulo duplicado.
    _p = capitais.pivot(index="data", columns="codigo_ibge", values="valor_rs")
    _cols = _p.notna().sum().sort_values(ascending=False).index  # mais longa primeiro
    clones = {}
    for _i, _keep in enumerate(_cols):
        for _cand in _cols[_i + 1 :]:
            if _cand in clones or _keep in clones:
                continue
            _both = _p[[_keep, _cand]].dropna()
            if (
                len(_both)
                and _both[_keep].eq(_both[_cand]).all()
                and (_p[_cand].notna() <= _p[_keep].notna()).all()
            ):
                clones[_cand] = _keep

    _nomes = capitais.drop_duplicates("codigo_ibge").set_index("codigo_ibge")
    _fmt = lambda c: f"{_nomes.at[c, 'municipio']} ({_nomes.at[c, 'uf']})"  # noqa: E731
    mo.md(
        "Séries clonadas removidas:\n\n"
        + "\n".join(f"- {_fmt(c)} = cópia de {_fmt(k)}" for c, k in clones.items())
        if clones
        else "Nenhuma série clonada."
    )
    return (clones,)


@app.cell
def _(KEY, capitais, clones, sp_df):
    dedup = capitais[~capitais["codigo_ibge"].isin(clones)]

    _sp = sp_df.rename(columns={"valor_rs": "valor_moeda_epoca"}).assign(codigo_ibge=3550308)
    merged = (
        dedup.merge(_sp, on=KEY, how="outer", validate="1:1", indicator=True)
        .sort_values(["uf", "municipio", "data"])
        .reset_index(drop=True)
    )
    assert (merged.pop("_merge") != "right_only").all(), "mês de SP ausente nas capitais"
    return (merged,)


@app.cell
def _(merged, mo):
    _sp = merged[merged["municipio"] == "São Paulo"].dropna(subset=["valor_moeda_epoca"])
    _iguais = _sp[_sp["valor_rs"].round(2) == _sp["valor_moeda_epoca"].round(2)]
    mo.vstack(
        [
            mo.md(
                f"**{len(merged):,}** linhas, **{merged['codigo_ibge'].nunique()}** capitais, "
                f"{merged['data'].min()} → {merged['data'].max()}. "
                f"Série SP DIEESE12 coincide com R$ a partir de **{_iguais['data'].min()}**."
            ),
            mo.ui.table(merged),
        ]
    )
    return


@app.cell
def _(OUT, merged, mo):
    OUT.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT / "cesta_basica_capitais.csv", index=False)
    merged.to_parquet(OUT / "cesta_basica_capitais.parquet", index=False)
    mo.md(f"Salvo em `{OUT}`")
    return


if __name__ == "__main__":
    app.run()
