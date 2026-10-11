#!/usr/bin/env bash
set -euo pipefail
CLUSTER_NAME="${CLUSTER_NAME:-upgrade-lab}"
if ! kind get clusters | grep -qx "${CLUSTER_NAME}"; then
  kind create cluster --name "${CLUSTER_NAME}"
fi
for version in v1.0 v1.1 v2.0; do
  kind load docker-image "cloud-upgrade-lab:${version}" --name "${CLUSTER_NAME}"
done
