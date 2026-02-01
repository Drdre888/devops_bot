#!/bin/bash
set -e
until PGPASSWORD=$PGPASSWORD psql -h "$MASTER_HOST" -U "$PGUSER" -c '\q' 2>/dev/null; do
  sleep 2
done
rm -rf /var/lib/postgresql/data/*
PGPASSWORD=123 pg_basebackup -h $MASTER_HOST -D /var/lib/postgresql/data -U replicator -P -v -R -X stream
