#!/bin/bash
# Fetch the synthetic customer profiles (Fernhollow Financial, Cedarline Health Network,
# Relaypoint) into data/customer-profiles/, which is gitignored.
#
# Pin REF to a tag or commit so every project tests against the same data. Override either
# value for one run: CUSTOMER_DATA_REF=v2 scripts/fetch-customer-data.sh
set -euo pipefail

REPO="${CUSTOMER_DATA_REPO:-https://github.com/hpk369/customer-profiles.git}"
REF="${CUSTOMER_DATA_REF:-HEAD}"  # HEAD = the repo's default branch; pin a tag once it exists
DEST="$(git rev-parse --show-toplevel)/data/customer-profiles"

if ! git ls-remote "$REPO" >/dev/null 2>&1; then
  echo "error: can't reach $REPO. Create the customer-profiles repo, or set CUSTOMER_DATA_REPO." >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST"
git -C "$DEST" init -q
git -C "$DEST" remote add origin "$REPO"
git -C "$DEST" fetch -q --depth 1 origin "$REF"
git -C "$DEST" checkout -q FETCH_HEAD
echo "fetched $REPO@$REF ($(git -C "$DEST" rev-parse --short HEAD)) into data/customer-profiles/"
