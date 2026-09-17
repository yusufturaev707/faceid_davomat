#!/usr/bin/env bash
# Frontend ni Debian serverda build qilish. Nginx to'g'ridan-to'g'ri
# `frontend/dist` papkasidan o'qiydi (root /var/www/faceid_davomat/frontend/dist).
#
# Build joyida (dist ustiga) bajarilsa, Vite avval papkani tozalaydi va sayt
# build davomida ishlamay turadi. Shuning uchun yangi versiya `dist.new` ga
# yig'iladi va oxirida bir lahzada almashtiriladi; eski versiya `dist.old`
# bo'lib qoladi (zarur bo'lsa darhol qaytarish uchun).
#
# Ishga tushirish: sudo bash deploy/frontend-deploy.sh

set -euo pipefail

PROJECT_DIR="/var/www/faceid_davomat"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
DIST_DIR="${FRONTEND_DIR}/dist"
NEW_DIR="${FRONTEND_DIR}/dist.new"
OLD_DIR="${FRONTEND_DIR}/dist.old"
WEB_OWNER="www-data:www-data"

# Build natijasida albatta bo'lishi kerak fayllar: admin panel va Mini App.
REQUIRED_FILES=("index.html" "miniapp/index.html")

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

echo "==> Build (vite) → dist.new"
rm -rf "${NEW_DIR}"
# `npm run build -- ...` qo'shimcha argumentlarni skript oxiriga, ya'ni
# `vite build` ga uzatadi (`tsc -b && vite build --outDir ...`).
NODE_OPTIONS="--max-old-space-size=2048" npm run build -- --outDir "${NEW_DIR}" --emptyOutDir

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${NEW_DIR}/${file}" ]]; then
        echo "Build muvaffaqiyatsiz — ${file} topilmadi" >&2
        rm -rf "${NEW_DIR}"
        exit 1
    fi
done

echo "==> Egalik va huquqlar: ${WEB_OWNER}"
chown -R "${WEB_OWNER}" "${NEW_DIR}"
# Nginx o'qiy olishi uchun: papkalarga kirish (x), fayllarga o'qish (r).
chmod -R a+rX "${NEW_DIR}"

echo "==> Yangi versiyani joyiga qo'yish"
rm -rf "${OLD_DIR}"
if [[ -d "${DIST_DIR}" ]]; then
    mv "${DIST_DIR}" "${OLD_DIR}"
fi
mv "${NEW_DIR}" "${DIST_DIR}"

# Nginx statik fayllarni papkadan o'qiydi — reload konfiguratsiya uchun emas,
# faqat tekshirish va keshlangan fayl deskriptorlarini yangilash uchun.
echo "==> Nginx konfiguratsiyasini tekshirish"
nginx -t

echo "==> Nginx reload"
systemctl reload nginx

# Nginx foydalanuvchisi haqiqatan ham o'qiy oladimi (yuqoridagi papkalarda
# kirish huquqi yetmasa, 403 chiqadi — buni deploy paytida bilib olamiz).
if id -u www-data >/dev/null 2>&1; then
    for file in "${REQUIRED_FILES[@]}"; do
        if ! sudo -u www-data test -r "${DIST_DIR}/${file}"; then
            echo "DIQQAT: www-data ${DIST_DIR}/${file} ni o'qiy olmayapti —" >&2
            echo "  yuqoridagi papkalar huquqini tekshiring (chmod o+x ...)" >&2
        fi
    done
fi

echo
echo "Tayyor."
echo "  Admin panel: ${DIST_DIR}/index.html"
echo "  Mini App:    ${DIST_DIR}/miniapp/index.html"
echo "  Eski versiya: ${OLD_DIR} (qaytarish: rm -rf ${DIST_DIR} && mv ${OLD_DIR} ${DIST_DIR})"
