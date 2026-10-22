#!/bin/bash
# Haal een ICON-D2 run op uit het publieke Open-Meteo archief (AWS Open Data)
# en bewaar enkel MSLP + windstoten voor het focusgebied als .npz.
#
# Gebruik: scripts/fetch_icon_d2.sh 2026/10/22/0900Z [doelmap]
set -euo pipefail
RUN=$1
OUT=${2:-data/icon_d2}
PY=${PYTHON:-python3}
HERE=$(cd "$(dirname "$0")" && pwd)
BUCKET=https://openmeteo.s3.amazonaws.com
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"

fetch_one() {
  local f=$1
  [ -f "$OUT/$f.npz" ] && return 0
  curl -sS -m 300 --retry 3 -o "$TMP/$f.om" "$BUCKET/data_spatial/dwd_icon_d2/$RUN/$f.om"
  "$PY" "$HERE/extract_icon_d2.py" "$TMP/$f.om" "$OUT/$f.npz"
  rm -f "$TMP/$f.om"
}
export -f fetch_one
export RUN OUT PY HERE BUCKET TMP

curl -sS "$BUCKET/?list-type=2&prefix=data_spatial/dwd_icon_d2/$RUN/" \
  | grep -oE "[0-9-]{10}T[0-9]{4}\.om" | sed 's/\.om$//' | sort -u \
  | xargs -P 6 -I{} bash -c 'fetch_one {}'
