#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

python -m pip install -r requirements.txt

python src/manage.py check
python src/manage.py collectstatic --noinput --clear
python src/manage.py migrate --noinput
