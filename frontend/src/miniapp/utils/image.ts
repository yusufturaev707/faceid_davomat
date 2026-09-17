/**
 * Kamera/galereya rasmini yuborishdan oldin kichraytirish.
 *
 * Telefon kamerasi 3–12 MP (base64'da 5–15 MB) beradi — backend limiti
 * (`MAX_BASE64_SIZE`) va mobil internet uchun og'ir. Bot kanalida Telegram
 * rasmni 1280px gacha o'zi siqardi; bu yerda xuddi shu o'lchamga keltiramiz.
 * `<img>` orqali chizish EXIF orientatsiyasini hisobga oladi (zamonaviy
 * WebView'lar) — selfie yonboshlab ketmaydi.
 */

export interface PreparedImage {
  /** Sof base64 (data URI prefiksisiz) — backendga yuboriladi. */
  base64: string;
  /** `<img src>` uchun data URI. */
  dataUrl: string;
}

function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Rasmni o'qib bo'lmadi. Boshqa rasm tanlang."));
    };
    img.src = url;
  });
}

export async function prepareImage(
  file: Blob,
  { maxSide, quality }: { maxSide: number; quality: number },
): Promise<PreparedImage> {
  const img = await loadImage(file);
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const width = Math.max(1, Math.round(img.naturalWidth * scale));
  const height = Math.max(1, Math.round(img.naturalHeight * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Rasmni qayta ishlab bo'lmadi.");
  ctx.drawImage(img, 0, 0, width, height);

  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  return { dataUrl, base64: dataUrl.slice(dataUrl.indexOf(",") + 1) };
}

export const SELFIE_OPTIONS = { maxSide: 1280, quality: 0.85 };
// QR kichik detal — kattaroq o'lcham va sifat saqlanadi.
export const QR_IMAGE_OPTIONS = { maxSide: 2000, quality: 0.92 };
