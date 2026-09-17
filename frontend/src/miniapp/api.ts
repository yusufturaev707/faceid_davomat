/**
 * Davomat Mini App API klienti (`/api/v1/davomat-miniapp`).
 *
 * Har so'rovda `Authorization: tma <initData>` — backend imzoni bot tokeni bilan
 * tekshiradi. Cookie/JWT/CSRF yo'q: admin panel klientidan (`src/api.ts`)
 * atayin alohida.
 */

import { telegram } from "./telegram";
import type {
  AbsenteesResponse,
  CheatResponse,
  FaceVerifyResponse,
  FindByJshshirResponse,
  FindForCheatResponse,
  MarkAttendanceResponse,
  MeResponse,
  PassportData,
  ReadySession,
  Reason,
  ReasonType,
  RemoveAttendanceResponse,
  SessionStats,
  StatsScope,
} from "./types";

const API_BASE = "/api/v1/davomat-miniapp";
// Face ID: GTSP (30s gacha) + yuz solishtirish — uzun kutish normal holat.
const REQUEST_TIMEOUT_MS = 90_000;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const FALLBACK_MESSAGES: Record<number, string> = {
  0: "Server bilan aloqa yo'q. Internetni tekshirib, qayta urinib ko'ring.",
  401: "Sessiya tasdiqlanmadi. Ilovani yopib, qaytadan oching.",
  403: "Bu amal uchun ruxsatingiz yo'q.",
  404: "Ma'lumot topilmadi.",
  429: "So'rovlar juda ko'p. Bir oz kutib, qayta urinib ko'ring.",
  503: "Xizmat vaqtincha ishlamayapti. Keyinroq urinib ko'ring.",
};

export function errorMessage(status: number, payload: unknown): string {
  if (payload && typeof payload === "object") {
    const { detail, errors } = payload as { detail?: unknown; errors?: unknown };
    if (Array.isArray(errors) && typeof errors[0] === "string") return errors[0];
    if (typeof detail === "string" && detail) return detail;
  }
  return FALLBACK_MESSAGES[status] ?? "Kutilmagan xatolik. Keyinroq urinib ko'ring.";
}

type Query = Record<string, string | number | null | undefined>;

async function request<T>(
  method: "GET" | "POST",
  path: string,
  options: { query?: Query; body?: unknown } = {},
): Promise<T> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== null && value !== undefined) params.set(key, String(value));
  }
  // `params.size` iOS 16 WebView'da yo'q — toString() bilan tekshiramiz.
  const qs = params.toString();
  const url = `${API_BASE}${path}${qs ? `?${qs}` : ""}`;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: {
        Authorization: `tma ${telegram.initData}`,
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, FALLBACK_MESSAGES[0]);
  } finally {
    window.clearTimeout(timer);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status, payload));
  return payload as T;
}

function scopeParams(scope: StatsScope) {
  return {
    session_smena_id: scope.kind === "smena" ? scope.smena.id : null,
    test_day: scope.kind === "day" ? scope.day : null,
  };
}

export const api = {
  me: () => request<MeResponse>("GET", "/me"),

  sessions: () => request<ReadySession[]>("GET", "/sessions"),

  stats: (sessionId: number, scope: StatsScope, regionId: number) =>
    request<SessionStats>("GET", `/sessions/${sessionId}/stats`, {
      query: { ...scopeParams(scope), region_id: regionId },
    }),

  sendAbsentees: (sessionId: number, scope: StatsScope, regionId: number) =>
    request<AbsenteesResponse>("POST", `/sessions/${sessionId}/absentees/send`, {
      body: { ...scopeParams(scope), region_id: regionId },
    }),

  passportFromQrText: (text: string) =>
    request<PassportData>("POST", "/passport-qr", { body: { text } }),

  passportFromQrImage: (imageB64: string) =>
    request<PassportData>("POST", "/passport-qr", { body: { image_b64: imageB64 } }),

  faceVerify: (body: {
    session_id: number;
    session_smena_id: number;
    region_id: number;
    ps_ser: string;
    ps_num: string;
    jshshir: string;
    selfie_b64: string;
  }) => request<FaceVerifyResponse>("POST", "/face-verify", { body }),

  markAttendance: (verifyTicket: string, selfieB64: string) =>
    request<MarkAttendanceResponse>("POST", "/mark-attendance", {
      body: { verify_ticket: verifyTicket, selfie_b64: selfieB64 },
    }),

  findByJshshir: (sessionSmenaId: number, regionId: number, jshshir: string) =>
    request<FindByJshshirResponse>("POST", "/find-by-jshshir", {
      body: { session_smena_id: sessionSmenaId, region_id: regionId, jshshir },
    }),

  removeAttendance: (studentId: number, sessionSmenaId: number, regionId: number) =>
    request<RemoveAttendanceResponse>("POST", "/remove-attendance", {
      body: { student_id: studentId, session_smena_id: sessionSmenaId, region_id: regionId },
    }),

  reasonTypes: () => request<ReasonType[]>("GET", "/reason-types"),

  reasons: (reasonTypeId: number) =>
    request<Reason[]>("GET", "/reasons", { query: { reason_type_id: reasonTypeId } }),

  findForCheat: (sessionId: number, regionId: number, jshshir: string) =>
    request<FindForCheatResponse>("POST", "/find-for-cheat", {
      body: { session_id: sessionId, region_id: regionId, jshshir },
    }),

  cheat: (studentId: number, sessionId: number, regionId: number, reasonId: number) =>
    request<CheatResponse>("POST", "/cheating", {
      body: {
        student_id: studentId,
        session_id: sessionId,
        region_id: regionId,
        reason_id: reasonId,
      },
    }),
};
