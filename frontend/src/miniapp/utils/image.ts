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

export interface ImageOptions {
  maxSide: number;
  quality: number;
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

/** Manba (rasm yoki video kadri) → kichraytirilgan JPEG. */
function render(
  source: CanvasImageSource,
  sourceWidth: number,
  sourceHeight: number,
  { maxSide, quality }: ImageOptions,
): PreparedImage {
  const scale = Math.min(1, maxSide / Math.max(sourceWidth, sourceHeight));
  const width = Math.max(1, Math.round(sourceWidth * scale));
  const height = Math.max(1, Math.round(sourceHeight * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Rasmni qayta ishlab bo'lmadi.");
  ctx.drawImage(source, 0, 0, width, height);

  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  return { dataUrl, base64: dataUrl.slice(dataUrl.indexOf(",") + 1) };
}

export async function prepareImage(file: Blob, options: ImageOptions): Promise<PreparedImage> {
  const img = await loadImage(file);
  return render(img, img.naturalWidth, img.naturalHeight, options);
}

/**
 * Jonli kameraning joriy kadrini olish — oqim to'xtamaydi, shuning uchun
 * operator bir necha marta "suratga olish" tugmasini bosa oladi.
 */
export function captureVideoFrame(video: HTMLVideoElement, options: ImageOptions): PreparedImage {
  const { videoWidth, videoHeight } = video;
  if (!videoWidth || !videoHeight) {
    throw new Error("Kamera tasviri hali tayyor emas. Bir soniya kutib, qayta urinib ko'ring.");
  }
  return render(video, videoWidth, videoHeight, options);
}

export const SELFIE_OPTIONS: ImageOptions = { maxSide: 1280, quality: 0.85 };
// QR kichik detal — kattaroq o'lcham va sifat saqlanadi.
export const QR_IMAGE_OPTIONS: ImageOptions = { maxSide: 2000, quality: 0.92 };
