#!/usr/bin/env bash
# Runs every reference implementation against fixtures.txt.
# Set VALIDATOR_LANGS to a subset (e.g. "python javascript") to skip languages you don't have installed.
set -euo pipefail
cd "$(dirname "$0")"

LANGS="${VALIDATOR_LANGS:-python javascript php java}"
PYTHON="${PYTHON:-python3}"

for lang in $LANGS; do
  echo "== $lang"
  case "$lang" in
    python)     "$PYTHON" -m unittest discover -s python -p 'test_*.py' ;;
    javascript) (cd javascript && node --test) ;;
    php)        php php/test.php ;;
    java)       out="$(mktemp -d)"; javac -d "$out" java/*.java
                java -cp "$out" TaiwanIdTest fixtures.txt
                # Turkish locale upper-cases "i" to "İ"; guards the Locale.ROOT call.
                java -Duser.language=tr -Duser.country=TR -cp "$out" TaiwanIdTest fixtures.txt ;;
    *)          echo "unknown language: $lang" >&2; exit 2 ;;
  esac
done
