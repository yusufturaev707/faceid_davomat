/**
 * Pasport seriya+raqami va JShShIR validatsiyasi — bot (`handlers/faceid.py`)
 * va backend (`normalize_ps_ser`) qoidalari bilan bir xil.
 */

// Foydalanuvchi klaviaturani almashtirib "AD" o'rniga kirillcha "АД" yozsa,
// ko'zga bir xil — lekin GTSP topa olmaydi. Faqat ko'rinishi bir xil harflar.
const CYRILLIC_TO_LATIN: Record<string, string> = {
  А: "A", В: "B", С: "C", Е: "E", Н: "H", К: "K", М: "M", О: "O", Р: "P", Т: "T",
  Х: "X", У: "Y", Д: "D",
};

export interface ParsedPassport {
  ps_ser: string;
  ps_num: string;
}

/** `ad 2311141`, `АД-2311141` → `{ ps_ser: "AD", ps_num: "2311141" }`; yaroqsiz → null. */
export function parsePassport(raw: string): ParsedPassport | null {
  const cleaned = Array.from(raw.replace(/[\s\-_]/g, "").toUpperCase())
    .map((ch) => CYRILLIC_TO_LATIN[ch] ?? ch)
    .join("");
  const match = /^([A-Z]{2})(\d{7})$/.exec(cleaned);
  return match ? { ps_ser: match[1], ps_num: match[2] } : null;
}

/** Kiritish maydoni uchun: faqat ruxsat etilgan belgilar, maksimal 9 ta. */
export function sanitizePassportInput(raw: string): string {
  return Array.from(raw.toUpperCase())
    .map((ch) => CYRILLIC_TO_LATIN[ch] ?? ch)
    .filter((ch) => /[A-Z0-9]/.test(ch))
    .join("")
    .slice(0, 9);
}

export function sanitizeJshshirInput(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 14);
}

export function isValidJshshir(value: string): boolean {
  return /^\d{14}$/.test(value);
}

/**
 * Native skaner o'qigan matn ID-karta QR'iga (MRZ) o'xshaydimi — tezkor
 * klient tekshiruvi. Aniq parsing backendda (`parse_passport_qr_text`).
 */
export function looksLikeIdCardQr(text: string): boolean {
  // Backend bilan bir xil pozitsiyalar: [5:14] seriya+raqam, [15:29] JShShIR.
  return /^.{5}[A-Z]{2}\d{7}.\d{14}/.test(text.trim().toUpperCase());
}
