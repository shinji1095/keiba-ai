#!/bin/sh
set -eu

: "${SCRAPE_SYNC_CRON:=5 0 * * *}"
: "${SCRAPE_SYNC_API_URL:=}"
: "${API_BASE_URL:=}"

CRON_FILE=/etc/cron.d/api-sync

cat > "$CRON_FILE" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SCRAPE_SYNC_API_URL=${SCRAPE_SYNC_API_URL:-$API_BASE_URL}
${SCRAPE_SYNC_CRON} root python /app/cron/cron_sync.py >> /var/log/api-sync-cron.log 2>&1
EOF

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"

exec cron -f
