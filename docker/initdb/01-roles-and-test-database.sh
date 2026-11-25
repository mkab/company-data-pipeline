#!/usr/bin/env bash
# Runs once, on an empty volume, as the owner role (POSTGRES_USER).
# Values reach psql as variables, so psql quotes them and they are never spliced into the SQL
set -euo pipefail

psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ingest_password="$INGEST_DB_PASSWORD" \
    --set dbt_password="$DBT_DB_PASSWORD" \
    --set api_password="$API_DB_PASSWORD" \
    --set database="$POSTGRES_DB" \
    <<'SQL'
CREATE ROLE ingest LOGIN PASSWORD :'ingest_password';
CREATE ROLE dbt LOGIN PASSWORD :'dbt_password';
CREATE ROLE api LOGIN PASSWORD :'api_password';

CREATE DATABASE pipeline_test;

-- dbt creates and owns the staging and curated schemas
GRANT CREATE ON DATABASE :"database" TO dbt;
GRANT CREATE ON DATABASE pipeline_test TO dbt;
SQL
