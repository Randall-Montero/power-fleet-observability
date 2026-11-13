#!/usr/bin/env bash
# scripts/create_gmail_secret.sh
# Create or update the Kubernetes Secret holding the Gmail App Password.
# The password is never written to disk or committed to Git.
#
# Usage:
#   bash scripts/create_gmail_secret.sh                 # prompts (input hidden)
#   GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx bash scripts/create_gmail_secret.sh
#
# Gmail App Password: https://myaccount.google.com/apppasswords (requires 2FA)
set -euo pipefail

NAMESPACE="power-fleet"

if [[ -z "${GMAIL_APP_PASSWORD:-}" ]]; then
  read -r -s -p "Gmail App Password (16 chars, input hidden): " GMAIL_APP_PASSWORD
  echo
fi
# Gmail displays the app password in groups separated by spaces; strip them.
GMAIL_APP_PASSWORD="${GMAIL_APP_PASSWORD// /}"
[[ -n "$GMAIL_APP_PASSWORD" ]] || { echo "Empty password" >&2; exit 1; }

kubectl create secret generic alertmanager-gmail \
  --namespace "$NAMESPACE" \
  --from-literal=gmail_password="$GMAIL_APP_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# Secret files are mounted as volumes, so Alertmanager must restart to read it.
kubectl rollout restart deployment/alertmanager -n "$NAMESPACE"
kubectl rollout status deployment/alertmanager -n "$NAMESPACE" --timeout=60s
echo "Secret alertmanager-gmail updated."
