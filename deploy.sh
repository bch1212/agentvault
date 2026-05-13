#!/usr/bin/env bash
set -euo pipefail

#──────────────────────────────────────────────────────────────────────
# AgentVault — deploy to Railway
#
# Prerequisites:
#   brew install railwayapp/tap/railway   (if not installed)
#   Copy RAILWAY_TOKEN from .deploy-secrets.env
#
# Usage:
#   cd agentvault && bash deploy.sh
#──────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Load shared secrets ──
SECRETS_FILE="../.deploy-secrets.env"
if [[ -f "$SECRETS_FILE" ]]; then
  set -a
  source "$SECRETS_FILE"
  set +a
  echo "✓ Loaded shared secrets"
else
  echo "✗ $SECRETS_FILE not found — set env vars manually"
fi

# ── Railway auth ──
# Avoid dual-token conflict
if [[ -n "${RAILWAY_TOKEN:-}" && -z "${RAILWAY_API_TOKEN:-}" ]]; then
  export RAILWAY_API_TOKEN="$RAILWAY_TOKEN"
  unset RAILWAY_TOKEN
fi

echo "── Checking Railway CLI ──"
if ! command -v railway &>/dev/null; then
  echo "Installing Railway CLI..."
  brew install railwayapp/tap/railway 2>/dev/null || npm i -g @railway/cli
fi

# ── Generate encryption key if needed ──
VAULT_KEY=""
if [[ -f .env ]] && grep -q "VAULT_ENCRYPTION_KEY=" .env; then
  VAULT_KEY=$(grep "VAULT_ENCRYPTION_KEY=" .env | cut -d= -f2-)
fi
if [[ -z "$VAULT_KEY" ]]; then
  echo "── Generating vault encryption key ──"
  VAULT_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo "VAULT_ENCRYPTION_KEY=$VAULT_KEY" >> .env
  echo "✓ Generated and saved VAULT_ENCRYPTION_KEY"
fi

# ── Create Stripe products + prices ──
echo "── Creating Stripe prices (idempotent via lookup_key) ──"
create_price() {
  local name=$1 amount=$2 lookup_key=$3
  existing=$(curl -s "https://api.stripe.com/v1/prices" \
    -u "${STRIPE_SECRET_KEY}:" \
    -d "lookup_keys[]=$lookup_key" \
    -G | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'] if d.get('data') else '')" 2>/dev/null || echo "")

  if [[ -n "$existing" ]]; then
    echo "  ✓ $name already exists: $existing"
    echo "$existing"
    return
  fi

  # Create product
  prod_id=$(curl -s "https://api.stripe.com/v1/products" \
    -u "${STRIPE_SECRET_KEY}:" \
    -d "name=AgentVault $name" \
    -d "metadata[app]=agentvault" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

  # Create price
  price_id=$(curl -s "https://api.stripe.com/v1/prices" \
    -u "${STRIPE_SECRET_KEY}:" \
    -d "product=$prod_id" \
    -d "unit_amount=$amount" \
    -d "currency=usd" \
    -d "recurring[interval]=month" \
    -d "lookup_key=$lookup_key" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

  echo "  ✓ Created $name: $price_id"
  echo "$price_id"
}

PRICE_PRO=$(create_price "Pro" 4900 "agentvault_pro")
PRICE_BIZ=$(create_price "Business" 14900 "agentvault_business")
PRICE_ENT=$(create_price "Enterprise" 49900 "agentvault_enterprise")

# ── Init Railway project ──
echo "── Setting up Railway project ──"
if ! railway status 2>/dev/null | grep -q "agentvault"; then
  railway init --name agentvault 2>/dev/null || true
fi
railway link 2>/dev/null || true

# ── Add Postgres ──
echo "── Ensuring Postgres plugin ──"
# Railway auto-provisions DATABASE_URL when you add Postgres via dashboard
# or we can set it via env vars after manual add
echo "  (If DATABASE_URL is not set after deploy, add Postgres via Railway dashboard)"

# ── Set env vars ──
echo "── Setting environment variables ──"
railway variables set \
  VAULT_ENCRYPTION_KEY="$VAULT_KEY" \
  STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY}" \
  STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-}" \
  STRIPE_PRICE_PRO="$PRICE_PRO" \
  STRIPE_PRICE_BUSINESS="$PRICE_BIZ" \
  STRIPE_PRICE_ENTERPRISE="$PRICE_ENT" \
  SENDGRID_API_KEY="${SENDGRID_API_KEY:-}" \
  SENDGRID_FROM_EMAIL="alerts@agentvault.dev" \
  ENVIRONMENT="production" \
  2>/dev/null || echo "  (set vars manually if railway variables fails)"

# ── Deploy ──
echo "── Deploying to Railway ──"
railway up --detach

echo ""
echo "════════════════════════════════════════════"
echo "  AgentVault deploy initiated!"
echo ""
echo "  Next steps:"
echo "  1. Add Postgres in Railway dashboard (if not auto-provisioned)"
echo "  2. Set DATABASE_URL env var (Railway auto-sets from Postgres plugin)"
echo "  3. Add custom domain: agentvault.dev"
echo "  4. Set up Stripe webhook → https://agentvault.dev/api/v1/billing/webhook"
echo "  5. Create Clerk app → set CLERK_SECRET_KEY, CLERK_JWKS_URL"
echo "════════════════════════════════════════════"
