#!/bin/sh
set -eu

: "${SCRAPE_SYNC_CRON:=5 0 * * *}"
: "${SCRAPE_SYNC_API_URL:=http://127.0.0.1:8001}"
: "${TZ:=Asia/Tokyo}"

# Debian cron uses the system timezone for scheduling.
ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime
printf '%s\n' "$TZ" > /etc/timezone

cat > /etc/cron.d/api-sync <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=${TZ}
SCRAPE_SYNC_API_URL=${SCRAPE_SYNC_API_URL}
${SCRAPE_SYNC_CRON} root python /app/cron/cron_sync.py >> /proc/1/fd/1 2>> /proc/1/fd/2
EOF
chmod 0644 /etc/cron.d/api-sync
exec cron -f
