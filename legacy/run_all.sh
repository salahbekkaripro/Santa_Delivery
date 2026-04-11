#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
FRONTEND_DIR="${ROOT_DIR}/frontend"
LOG_DIR="${ROOT_DIR}/cache/run_all"

RUN_TESTS=1
RUN_BACKEND=1
RUN_FRONTEND=1

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

usage() {
  cat <<'EOF'
Usage: ./run_all.sh [options]

Options:
  --skip-tests      Do not run backend tests before launch
  --skip-backend    Do not start FastAPI
  --skip-frontend   Do not start Next.js
  -h, --help        Show this help

Env overrides:
  BACKEND_HOST=127.0.0.1
  BACKEND_PORT=8000
  FRONTEND_PORT=3000
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests)
      RUN_TESTS=0
      shift
      ;;
    --skip-backend)
      RUN_BACKEND=0
      shift
      ;;
    --skip-frontend)
      RUN_FRONTEND=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Option inconnue: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Environnement virtuel introuvable: ${VENV_PYTHON}" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "Frontend introuvable: ${FRONTEND_DIR}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"

BACKEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo
    echo "Arret du backend (${BACKEND_PID})..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

if [[ "${RUN_TESTS}" -eq 1 ]]; then
  echo "==> Tests backend"
  "${VENV_PYTHON}" -m unittest tests.test_api tests.test_routing_payloads tests.test_repository
fi

if [[ "${RUN_BACKEND}" -eq 1 ]]; then
  echo "==> Lancement backend FastAPI sur http://${BACKEND_HOST}:${BACKEND_PORT}"
  "${VENV_PYTHON}" -m uvicorn backend.app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" --reload \
    > "${LOG_DIR}/backend.log" 2>&1 &
  BACKEND_PID=$!
fi

echo "==> URLs"
if [[ "${RUN_BACKEND}" -eq 1 ]]; then
  echo "API     : http://${BACKEND_HOST}:${BACKEND_PORT}"
  echo "Docs    : http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
  echo "Logs API: ${LOG_DIR}/backend.log"
fi
if [[ "${RUN_FRONTEND}" -eq 1 ]]; then
  echo "Frontend: http://localhost:${FRONTEND_PORT}"
fi

if [[ "${RUN_FRONTEND}" -eq 1 ]]; then
  echo "==> Lancement frontend Next.js"
  cd "${FRONTEND_DIR}"
  exec npm run dev -- --port "${FRONTEND_PORT}"
fi

if [[ "${RUN_BACKEND}" -eq 1 ]]; then
  echo "Backend actif. CTRL+C pour quitter."
  wait "${BACKEND_PID}"
fi
