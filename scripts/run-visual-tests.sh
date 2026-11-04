#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker build -q --platform linux/amd64 -f "$repo_root/frontend/Dockerfile.visual" -t retrosprint-playwright-visual "$repo_root/frontend"
docker run --rm --init --ipc=host --platform linux/amd64 \
  -v "$repo_root:/workspace" -w /workspace \
  -v /workspace/frontend/node_modules -v /workspace/frontend/.nuxt \
  -v /workspace/backend/.venv \
  -e NUXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  -e RETROSPRINT_VISUAL_TEST=1 \
  retrosprint-playwright-visual \
  bash -lc 'mise trust mise.toml && mise install --locked && mise run setup && mise exec -- pnpm --dir frontend generate && mise exec -- pnpm --dir frontend test:e2e --grep "retrieval purpose" "$@"' bash "$@"
