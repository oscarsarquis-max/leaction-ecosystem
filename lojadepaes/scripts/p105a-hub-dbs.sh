#!/usr/bin/env bash
set -eu
sudo -u postgres psql -d postgres -tAc "SELECT datname FROM pg_database WHERE datname NOT IN ('template0','template1') ORDER BY 1;"
