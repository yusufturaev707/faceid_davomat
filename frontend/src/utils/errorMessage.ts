import axios from "axios";

/**
 * Backend xatosidan tushunarli xabar olish.
 *
 * FastAPI xatolarni quyidagi formatlarda qaytaradi:
 *   - { detail: "..." }                  — oddiy string
 *   - { detail: [{ msg: "...", loc: [...] }] }  — validation errors
 *   - string (plain text)
 *
 * Agar backend javob bermasa — tarmoq xatosi.
 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data;

    // Backend validation xatosi (Pydantic)
    if (data?.detail && Array.isArray(data.detail)) {
      return data.detail
        .map((e: any) => {
          const field = e.loc?.slice(-1)[0] || "";
          const msg = e.msg || "";
          return field ? `${field}: ${msg}` : msg;
        })
        .join("; ");
    }

    // Backend oddiy xato xabari
    if (data?.detail && typeof data.detail === "string") {
      return data.detail;
    }

    // Backend boshqa string javob
    if (typeof data === "string" && data.length > 0 && data.length < 300) {
      return data;
    }

    // HTTP status code bo'yicha tushunarli xabar
    if (status) {
      const statusMessages: Record<number, string> = {
        400: "So'rov noto'g'ri yuborildi",
        401: "Avtorizatsiya talab qilinadi. Qayta kiring",
        403: "Ruxsat yo'q. Admin huquqi kerak",
        404: "Ma'lumot topilmadi",
        409: "Bunday ma'lumot allaqachon mavjud",
        422: "Kiritilgan ma'lumotlar noto'g'ri",
        429: "So'rovlar soni cheklangan. Biroz kuting",
        500: "Serverda ichki xatolik yuz berdi. Keyinroq urinib ko'ring",
        502: "Server vaqtincha ishlamayapti",
        503: "Server yuklanib ketgan. Keyinroq urinib ko'ring",
      };
      return statusMessages[status] || `Xatolik (${status})`;
    }

    // Tarmoq xatosi (server javob bermadi)
    if (error.code === "ERR_NETWORK") {
      return "Serverga ulanib bo'lmadi. Internet aloqasini tekshiring";
    }
    if (error.code === "ECONNABORTED") {
      return "So'rov vaqti tugadi. Server javob bermadi";
    }

    return "Tarmoq xatosi. Internet aloqasini tekshiring";
  }

  // JS xatosi
  if (error instanceof Error) {
    return error.message;
  }

  return "Noma'lum xatolik yuz berdi";
}
