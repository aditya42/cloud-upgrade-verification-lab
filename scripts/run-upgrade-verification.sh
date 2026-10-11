#!/usr/bin/env bash
set -euo pipefail
./scripts/build-releases.sh
./scripts/kind-up.sh
pytest -m e2e -v tests/e2e
