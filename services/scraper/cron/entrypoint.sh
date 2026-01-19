#!/bin/sh
set -eu

: "${SCRAPER_CRON:=*/2 * * * *}"
: "${SCRAPER_CONTROL_URL:=}"

CRON_FILE=/etc/cron.d/scraper

cat > "$CRON_FILE" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SCRAPER_CONTROL_URL=${SCRAPER_CONTROL_URL}
PYTHONPATH=/app
${SCRAPER_CRON} root python /app/cron/cron_run.py >> /var/log/scraper-cron.log 2>&1
EOF

chmod 0644 "$CRON_FILE"

exec cron -f
