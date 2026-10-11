#!/usr/bin/env bash
set -euo pipefail
for version in v1.0 v1.1 v2.0; do
  echo "==> Building cloud-upgrade-lab:${version}"
  docker build --build-arg RELEASE_VERSION="${version}" -t "cloud-upgrade-lab:${version}" .
done
