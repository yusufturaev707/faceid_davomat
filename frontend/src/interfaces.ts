/** Backend Pydantic sxemalariga mos TypeScript interfeyslari */

// === Photo ===
export interface PhotoVerifyRequest {
  age: number;
  img_b64: string;
}

export interface ImageSize {
  height: number;
  width: number;
}

export interface PalitraRGB {
  min_palitra: number[];
  max_palitra: number[];
}

export interface PhotoVerifyResponse {
  success: boolean;
  back_color: number[];
  size: ImageSize;
  palitra_rgb: PalitraRGB;
  detection: boolean;
  file_size_byte: number;
  error_messages: string[];
}

// === Auth ===
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenPairResponse {
  access_token: string;
  token_type: string;
  user?: UserResponse;
}

export interface UserResponse {
  id: number;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

// === Admin ===
export interface VerificationLogResponse {
  id: number;
  user_id: number;
  username: string;
  timestamp: string;
  success: boolean;
  detection: boolean;
  image_width: number;
  image_height: number;
  file_size_bytes: number;
  input_age: number;
  back_color: string | null;
  error_message: string | null;
  image_path: string | null;
}

export interface PaginatedLogs {
  items: VerificationLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DailyChartItem {
  date: string;
  count: number;
}

export interface DashboardStats {
  total_verifications: number;
  today_verifications: number;
  week_verifications: number;
  success_rate: number;
  unique_users: number;
  daily_chart: DailyChartItem[];
}

export interface CreateUserRequest {
  username: string;
  password: string;
  full_name?: string;
  role?: string;
}

export interface ErrorResponse {
  detail: string;
}

export interface TaskSubmitResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: PhotoVerifyResponse;
  error?: string;
}

// === Ikki yuzni solishtirish ===
export interface TwoFaceVerifyRequest {
  ps_img: string;
  lv_img: string;
}

export interface TwoFaceVerifyResponse {
  score: number;
  thresh_score: number;
  verified: boolean;
  message: string;
  ps_detection: boolean;
  lv_detection: boolean;
  ps_file_size: number;
  lv_file_size: number;
  ps_width: number;
  ps_height: number;
  lv_width: number;
  lv_height: number;
  error_messages: string[];
}

export interface TwoFaceTaskStatusResponse {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: TwoFaceVerifyResponse;
  error?: string;
}

// === Admin: Yuz solishtirish loglari ===
export interface FaceLogResponse {
  id: number;
  user_id: number;
  username: string;
  timestamp: string;
  ps_img: string | null;
  lv_img: string | null;
  ps_file_size: number;
  lv_file_size: number;
  ps_width: number;
  ps_height: number;
  lv_width: number;
  lv_height: number;
  ps_detection: boolean;
  lv_detection: boolean;
  detection: boolean;
  response_time: number;
  score: number;
  thresh_score: number;
  verified: boolean;
  error_message: string | null;
}

export interface PaginatedFaceLogs {
  items: FaceLogResponse[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// === Embedding ===
export interface EmbeddingRequest {
  img_b64: string;
}

export interface EmbeddingResponse {
  detection: boolean;
  embedding: number[];
  embedding_size: number;
  file_size_byte: number;
  image_width: number;
  image_height: number;
  error_messages: string[];
}

// === API Key ===
export interface ApiKeyCreateRequest {
  name: string;
}

export interface ApiKeyCreateResponse {
  id: number;
  name: string;
  prefix: string;
  raw_key: string;
  created_at: string;
}

export interface ApiKeyResponse {
  id: number;
  user_id: number;
  name: string;
  prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}
