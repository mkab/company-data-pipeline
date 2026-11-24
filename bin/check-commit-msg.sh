#!/bin/bash
set -e

COMMIT_MSG_FILE=$1

# Regex for allowed prefixes
if ! grep -qE '^(feat|fix|chore): ' "$COMMIT_MSG_FILE"; then
    echo "ERROR: Commit message must start with feat:, fix:, or chore: *"
    exit 1
fi
