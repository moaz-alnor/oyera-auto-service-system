#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

is_enabled() {
    normalized_value="$(
        printf '%s' "$1" |
            tr '[:upper:]' '[:lower:]'
    )"

    test "$normalized_value" = "true"
}

printf 'Running OYERA production system check...\n'
python src/manage.py check

if is_enabled "${OYERA_RUN_MIGRATIONS:-true}"; then
    printf 'Applying database migrations...\n'
    python src/manage.py migrate --noinput
else
    printf 'Automatic migrations are disabled.\n'
fi

if is_enabled "${OYERA_COLLECT_STATIC:-true}"; then
    printf 'Collecting production static files...\n'
    python src/manage.py collectstatic --noinput
else
    printf 'Automatic static collection is disabled.\n'
fi

printf 'Starting OYERA with Gunicorn...\n'

exec gunicorn \
    --config gunicorn.conf.py \
    config.wsgi:application
