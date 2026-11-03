#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cp docs/index.html tizen-app/index.html
printf 'Synchronized Tizen UI from docs/index.html\n'
