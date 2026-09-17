/** Backend `schemas/davomat_bot.py` va `schemas/davomat_miniapp.py` ko'zgusi. */

export interface Region {
  id: number;
  name: string;
  number: number;
}

export interface Operator {
  id: number;
  fio: string;
  telegram_id: number;
  is_active: boolean;
  role: { id: number; name: string; key: number } | null;
  regions: Region[];
  allowed_region_ids: number[];
}

export interface MeResponse {
  allowed: boolean;
  telegram_id: number;
  user: Operator | null;
  message: string | null;
}

export interface SmenaInfo {
  /** TestSessionSmena.id */
  id: number;
  smena_id: number;
  smena_number: number;
  smena_name: string;
  /** YYYY-MM-DD */
  day: string;
}

export interface ReadySession {
  id: number;
  name: string;
  test_name: string;
  start_date: string;
  finish_date: string;
  smenas: SmenaInfo[];
}

export interface AttendanceCounts {
  total: number;
  entered: number;
  not_entered: number;
  cheating: number;
}

export interface ZoneStat extends AttendanceCounts {
  zone_id: number;
  zone_name: string;
  zone_number: number;
}

export interface RegionStat extends AttendanceCounts {
  region_id: number;
  region_name: string;
  region_number: number;
  zones: ZoneStat[];
}

export interface SessionStats {
  session_id: number;
  session_smena_id: number;
  test_day: string | null;
  smena_number: number;
  smena_name: string;
  scope: "smena" | "day" | "total";
  title: string;
  regions: RegionStat[];
}

/** Statistika/Excel konteksti: bitta smena, bitta kun yoki butun sessiya. */
export type StatsScope =
  | { kind: "smena"; smena: SmenaInfo }
  | { kind: "day"; day: string }
  | { kind: "total" };

export interface AbsenteesResponse {
  status: "sent" | "empty";
  count: number;
  filename: string;
  message: string;
}

export interface PassportData {
  ps_ser: string;
  ps_num: string;
  jshshir: string;
}

export interface StudentSlot {
  student_id: number;
  fio: string;
  jshshir: string | null;
  region_name: string | null;
  zone_name: string | null;
  test_day: string | null;
  smena_number: number | null;
  smena_name: string | null;
  gr_n: number | null;
  sp_n: number | null;
  subject_name: string | null;
  is_applied: boolean;
  is_entered: boolean;
}

export type FaceVerifyStatus =
  | "in_smena"
  | "wrong_slot"
  | "not_in_session"
  | "wrong_passport"
  | "no_face"
  | "applied"
  | "error";

export interface FaceVerifyResponse {
  status: FaceVerifyStatus;
  verified: boolean;
  score: number;
  threshold: number;
  can_attend: boolean;
  fio: string | null;
  photo_b64: string | null;
  message: string;
  slot: StudentSlot | null;
  verify_ticket: string | null;
}

export interface MarkAttendanceResponse {
  status: "ok" | "already_entered" | "applied" | "not_found" | "error";
  student_id: number | null;
  log_id: number | null;
  message: string;
}

export interface FindByJshshirResponse {
  status: "ok" | "not_found" | "error";
  matches: StudentSlot[];
  message: string;
}

export interface RemoveAttendanceResponse {
  status: "ok" | "not_entered" | "not_found" | "error";
  student_id: number | null;
  message: string;
}

export interface ReasonType {
  id: number;
  name: string;
  key: number;
}

export interface Reason {
  id: number;
  reason_type_id: number | null;
  name: string;
  key: number;
}

export interface FindForCheatResponse {
  status: "ok" | "not_found" | "already_cheating" | "error";
  matches: StudentSlot[];
  message: string;
}

export interface CheatResponse {
  status: "ok" | "already_cheating" | "invalid_reason" | "not_found" | "wrong_session" | "error";
  student_id: number | null;
  log_id: number | null;
  message: string;
}
