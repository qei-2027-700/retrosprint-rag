"""Export the development contract without running a server or loading local settings."""

import json
from pathlib import Path

from retrosprint_rag.main import Settings, create_app

OUTPUT = Path(__file__).resolve().parents[2] / "frontend/openapi/openapi.json"


def main() -> None:
    app = create_app(Settings(_env_file=None, enable_dev_api=True, cors_origins=[]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
