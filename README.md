# python-pandas-notebooks-playground

Playground de notebooks [marimo](https://marimo.io) com pandas, gerenciado com [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync                  # cria .venv com Python 3.13 e instala tudo (inclui grupo dev)
cp .env.example .env     # ajuste as variáveis locais
```

## Uso

```bash
uv run marimo edit notebooks/            # abre o editor com todos os notebooks
uv run marimo edit notebooks/novo.py     # cria/edita um notebook
uv run marimo run notebooks/00_inicio.py # roda como app (somente leitura)
uv run python notebooks/00_inicio.py     # executa como script
```

Notebooks marimo são arquivos `.py` puros: diffs limpos no git, sem outputs salvos.
No VSCode, use a extensão `marimo-team.vscode-marimo`.

Dentro dos notebooks:

```python
import pandas as pd

from playground import PROCESSED_DIR, RAW_DIR, settings

df = pd.read_csv(RAW_DIR / "arquivo.csv")
settings.API_KEY  # lê do .env
```

## Dependências

```bash
uv add polars            # dependência de runtime
uv add --dev seaborn     # dependência só de desenvolvimento
uv lock --upgrade        # atualiza o lockfile
```

## Qualidade

```bash
uv run ruff check .      # lint (inclui os notebooks)
uv run ruff format .     # formatação
```

## Estrutura

```
data/raw/         dados brutos (ignorados pelo git)
data/processed/   dados gerados (ignorados pelo git)
notebooks/        notebooks marimo (.py)
src/playground/   código reutilizável importável nos notebooks
```
