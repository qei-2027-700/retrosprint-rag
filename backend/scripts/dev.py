"""Regenerate the API contract before starting each development server process."""

import subprocess
from pathlib import Path

from fastapi import FastAPI

from retrosprint_rag.main import create_app


def create_dev_app() -> FastAPI:
    root = Path(__file__).resolve().parents[2]
    subprocess.run(["mise", "run", "api:generate"], cwd=root, check=True)
    return create_app()
