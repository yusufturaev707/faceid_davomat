/**
 * ID-karta QR'ini ilova ichida (brauzer kamerasi bilan) o'qish.
 *
 * Telegram native skaneri faqat mobil klientlarda bor (`telegram.canScanQr`),
 * Desktop/Web'da esa yo'q. Shuning uchun ilovaning o'zi ham kamerani ocha
 * oladi va kadrlarni ikki yo'l bilan dekodlaydi:
 *   - `BarcodeDetector` (Chromium: Android WebView, Telegram Desktop) — kadr
 *     jonli, serverga bormasdan o'qiladi;
 *   - detektor yo'q bo'lsa (iOS WebKit) — operator suratga oladi va kadr
 *     backendga (`/passport-qr`, zxing-cpp) yuboriladi.
 * Ikkalasi ham tashqi npm paketisiz ishlaydi.
 */

import { looksLikeIdCardQr } from "./passport";

interface DetectedBarcode {
  rawValue: string;
}

interface BarcodeDetectorLike {
  detect(source: CanvasImageSource): Promise<DetectedBarcode[]>;
}

interface BarcodeDetectorCtor {
  new (options?: { formats?: string[] }): BarcodeDetectorLike;
  getSupportedFormats?: () => Promise<string[]>;
}

declare global {
  interface Window {
    BarcodeDetector?: BarcodeDetectorCtor;
  }
}

export interface QrDetector {
  /** Kadrdagi barcha QR matnlari (topilmasa — bo'sh ro'yxat). */
  detect(source: CanvasImageSource): Promise<string[]>;
}

/** Jonli dekodlash mumkin bo'lsa detektor, aks holda `null`. */
export async function createQrDetector(): Promise<QrDetector | null> {
  const Ctor = typeof window !== "undefined" ? window.BarcodeDetector : undefined;
  if (!Ctor) return null;
  try {
    // Chrome'da konstruktor bor, lekin platformada `qr_code` bo'lmasligi mumkin.
    const formats = await Ctor.getSupportedFormats?.();
    if (formats && !formats.includes("qr_code")) return null;
    const detector = new Ctor({ formats: ["qr_code"] });
    return {
      detect: async (source) => (await detector.detect(source)).map((code) => code.rawValue || ""),
    };
  } catch {
    return null;
  }
}

/**
 * Kadrda bir nechta QR bo'lishi mumkin (plakat, boshqa hujjat) — faqat
 * ID-karta MRZ'siga o'xshaganini olamiz. `skip` — allaqachon urinib ko'rilgan
 * va backend rad etgan matnlar: bir xil noto'g'ri QR qayta-qayta yuborilmaydi.
 */
export function findIdCardQr(texts: string[], skip?: ReadonlySet<string>): string | null {
  for (const raw of texts) {
    const text = (raw || "").trim();
    if (!text || skip?.has(text)) continue;
    if (looksLikeIdCardQr(text)) return text;
  }
  return null;
}

/** `getUserMedia` xatosini operator tushunadigan matnga aylantirish. */
export function cameraErrorMessage(error: unknown): string {
  const name = (error as { name?: string } | null)?.name ?? "";
  switch (name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return (
        "Kameraga ruxsat berilmadi. Telegram sozlamalarida kameraga ruxsat bering " +
        "yoki QR rasmini yuklang."
      );
    case "NotFoundError":
    case "DevicesNotFoundError":
    case "OverconstrainedError":
      return "Qurilmada kamera topilmadi. QR rasmini yuklang yoki ma'lumotlarni qo'lda kiriting.";
    case "NotReadableError":
    case "TrackStartError":
    case "AbortError":
      return "Kamera band — uni ishlatayotgan boshqa ilovani yopib, qayta urinib ko'ring.";
    default:
      return "Kamerani ochib bo'lmadi. QR rasmini yuklang yoki ma'lumotlarni qo'lda kiriting.";
  }
}

/** Kamera umuman mumkinmi: HTTPS (yoki localhost) va `getUserMedia` API. */
export function cameraUnavailableReason(): string | null {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    // Eski WebView yoki HTTP orqali ochilgan sahifa — API umuman yo'q.
    return typeof window !== "undefined" && window.isSecureContext === false
      ? "Kamera faqat HTTPS orqali ochilgan ilovada ishlaydi. QR rasmini yuklang."
      : "Bu qurilmada ilova ichidagi kamera ishlamaydi. QR rasmini yuklang.";
  }
  return null;
}

/** Oqimdagi barcha trekni to'xtatish — kamera chiroqchasi o'chishi uchun majburiy. */
export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}
