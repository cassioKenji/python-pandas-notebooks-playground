import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Início

    Notebook de exemplo: verifica o ambiente e o carregamento do `.env`.
    """)
    return


@app.cell
def _():
    import numpy as np
    import pandas as pd

    from playground import PROCESSED_DIR, RAW_DIR

    print(pd.__version__, RAW_DIR, PROCESSED_DIR)
    return np, pd


@app.cell
def _(np, pd):
    df = pd.DataFrame({"x": np.arange(10), "y": np.random.default_rng(42).normal(size=10)})
    df.describe()
    return


if __name__ == "__main__":
    app.run()
