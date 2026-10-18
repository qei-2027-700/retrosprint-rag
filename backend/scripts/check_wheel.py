"""Install the wheel into a clean environment and serve HTTP outside the source tree."""

import os
import socket
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

import httpx


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((backend_root / "pyproject.toml").read_text())["project"]
    wheel = backend_root / "dist" / f"retrosprint_rag-{project['version']}-py3-none-any.whl"
    with tempfile.TemporaryDirectory(prefix="retrosprint-wheel-") as directory:
        root = Path(directory)
        subprocess.run(["uv", "venv", str(root / "venv")], check=True)
        python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        constraints = root / "constraints.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--project",
                str(backend_root),
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(constraints),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--constraint",
                str(constraints),
                str(wheel),
            ],
            check=True,
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "retrosprint_rag.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env={**os.environ, "RETROSPRINT_ENABLE_DEV_API": "false"},
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Wheel server exited before becoming ready")
                    try:
                        response = client.get("/health")
                        response.raise_for_status()
                        assert response.json() == {"status": "ok"}
                        assert client.post("/api/v1/dev/echo").status_code == 404
                        print(
                            "Installed wheel: import, HTTP health and public configuration passed"
                        )
                        return
                    except httpx.ConnectError:
                        time.sleep(0.1)
                raise RuntimeError("Wheel server did not become ready")
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
