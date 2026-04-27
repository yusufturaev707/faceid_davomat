#!/usr/bin/env bash
# FaceID Celery systemd birliklarini o'rnatish skripti.
# Debian/Ubuntu serverda root sifatida ishga tushiring: sudo ./install.sh

set -euo pipefail

PROJECT_DIR="/var/www/faceid_davomat/backend"
LOG_DIR="${PROJECT_DIR}/logs"
SERVICE_USER="root"
SERVICE_GROUP="www-data"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Bu skript root huquqi bilan ishga tushirilishi kerak (sudo ./install.sh)" >&2
    exit 1
fi

if [[ ! -d "${PROJECT_DIR}" ]]; then
    echo "Loyiha papkasi topilmadi: ${PROJECT_DIR}" >&2
    exit 1
fi

if [[ ! -x "${PROJECT_DIR}/venv/bin/celery" ]]; then
    echo "Celery binar fayli topilmadi: ${PROJECT_DIR}/venv/bin/celery" >&2
    echo "Avval venv yarating va requirements.txt ni o'rnating." >&2
    exit 1
fi

echo "Log papkasi tayyorlanmoqda: ${LOG_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0755 "${LOG_DIR}"

echo "Loyiha egaligi to'g'rilanmoqda"
chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${PROJECT_DIR}/uploads" 2>/dev/null || true

echo "Service fayllari ${SYSTEMD_DIR} ga ko'chirilmoqda"
install -m 0644 "${SCRIPT_DIR}/faceid-celery-verify.service"  "${SYSTEMD_DIR}/"
install -m 0644 "${SCRIPT_DIR}/faceid-celery-storage.service" "${SYSTEMD_DIR}/"
install -m 0644 "${SCRIPT_DIR}/faceid-celery.target"          "${SYSTEMD_DIR}/"

echo "systemd qayta yuklanmoqda"
systemctl daemon-reload

echo "Servicelar enable qilinmoqda"
systemctl enable faceid-celery-verify.service
systemctl enable faceid-celery-storage.service
systemctl enable faceid-celery.target

echo "Servicelar ishga tushirilmoqda"
systemctl restart faceid-celery.target

sleep 2
systemctl --no-pager status faceid-celery-verify.service  | head -n 12 || true
echo "---"
systemctl --no-pager status faceid-celery-storage.service | head -n 12 || true

echo
echo "Tayyor. Foydali komandalar:"
echo "  sudo systemctl status  faceid-celery.target"
echo "  sudo systemctl restart faceid-celery.target"
echo "  sudo systemctl stop    faceid-celery.target"
echo "  sudo journalctl -u faceid-celery-verify  -f"
echo "  sudo journalctl -u faceid-celery-storage -f"
