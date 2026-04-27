#!/usr/bin/env bash
# Frontend ni Debian serverda build qilib, Nginx web rootga ko'chirish.
# Ishga tushirish: sudo bash deploy/frontend-deploy.sh

set -euo pipefail

PROJECT_DIR="/var/www/faceid_davomat"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
WEB_ROOT="${PROJECT_DIR}/web"
WEB_OWNER="www-data:www-data"

if [[ $EUID -ne 0 ]]; then
    echo "sudo bilan ishga tushiring" >&2
    exit 1
fi

if [[ ! -d "${FRONTEND_DIR}" ]]; then
    echo "Frontend papkasi topilmadi: ${FRONTEND_DIR}" >&2
    exit 1
fi

echo "==> Git yangilash"
git -C "${PROJECT_DIR}" pull --ff-only

echo "==> npm ci"
cd "${FRONTEND_DIR}"
npm ci

echo "==> Build (vite)"
NODE_OPTIONS="--max-old-space-size=2048" npm run build

if [[ ! -d "${FRONTEND_DIR}/dist" ]]; then
    echo "Build muvaffaqiyatsiz — dist/ topilmadi" >&2
    exit 1
fi

echo "==> Web rootga ko'chirish: ${WEB_ROOT}"
mkdir -p "${WEB_ROOT}"
rsync -a --delete "${FRONTEND_DIR}/dist/" "${WEB_ROOT}/"
chown -R "${WEB_OWNER}" "${WEB_ROOT}"

echo "==> Nginx konfiguratsiyasini tekshirish"
nginx -t

echo "==> Nginx reload"
systemctl reload nginx

echo
echo "Tayyor. Sayt yangilandi: ${WEB_ROOT}"
