"""Carrega variáveis do .env e expõe caminhos do projeto."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Caminhos relativos no .env são resolvidos a partir da raiz do projeto,
# não do diretório onde o notebook está rodando.
DATA_DIR = (PROJECT_ROOT / os.getenv("DATA_DIR", "data")).resolve()
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


class _Settings:
    def __getattr__(self, name: str) -> str | None:
        return os.getenv(name)


settings = _Settings()
