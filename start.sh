#!/usr/bin/env bash
# start.sh - Lance les deux apps Blackjack Trainer Pro en parallèle.
# Usage : ./start.sh
# Arrêt  : Ctrl+C stoppe proprement les deux processus.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "🃏  Blackjack Trainer Pro"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Créer .env depuis .env.example si absent ──────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅  .env créé depuis .env.example"
fi

# ── Charger les variables ──────────────────────────────────────
set -a
# shellcheck disable=SC1091
source .env
set +a

VITE_PORT="${VITE_PORT:-5173}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# ── Propager VITE_* dans react/.env pour le dev server ────────
# (Vite lit react/.env depuis son répertoire de travail)
if [ ! -f react/.env ]; then
  grep "^VITE_" .env > react/.env 2>/dev/null || true
  echo "✅  react/.env créé (variables VITE_*)"
fi

# ── Démarrer Streamlit en arrière-plan ────────────────────────
echo ""
echo "📊  Démarrage du simulateur sur le port ${STREAMLIT_PORT}..."
streamlit run app_simulation.py \
  --server.port "${STREAMLIT_PORT}" \
  --server.headless true \
  --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# ── Démarrer Vite en arrière-plan ─────────────────────────────
echo "🃏  Démarrage du jeu sur le port ${VITE_PORT}..."
cd react
npm run dev -- --port "${VITE_PORT}" &
VITE_PID=$!
cd "$REPO_DIR"

# ── Résumé ────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Les deux apps sont lancées :"
echo "   🃏  Jeu         →  http://localhost:${VITE_PORT}"
echo "   📊  Simulateur  →  http://localhost:${STREAMLIT_PORT}"
echo ""
echo "Ctrl+C pour tout arrêter."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Arrêt propre sur Ctrl+C ───────────────────────────────────
cleanup() {
  echo ""
  echo "Arrêt en cours..."
  kill "$STREAMLIT_PID" "$VITE_PID" 2>/dev/null || true
  # Attendre la fin des deux processus
  wait "$STREAMLIT_PID" 2>/dev/null || true
  wait "$VITE_PID"      2>/dev/null || true
  echo "✅  Arrêté proprement."
  exit 0
}
trap cleanup INT TERM

wait
