/** Access tokenni sessionStorage'da saqlash.
 * - F5 da saqlanadi → har F5 da `/auth/refresh` chaqirilmaydi
 * - Tab yopilganda o'chadi → yangi tab/sessiyada refresh chaqiriladi
 * - localStorage emas — XSS xavfini cheklaydi.
 *   Access token TTL 15 daqiqa (admin uchun 10) — o'g'irlangan token zarari kichik.
 *   Logout darhol Redis blacklist bilan ham bekor qilinadi.
 */
const STORAGE_KEY = "faceid_access_token";

// Memory cache — har getAccessToken da sessionStorage o'qishni o'tkazib yuboramiz
let cached: string | null = null;
let initialized = false;

function loadFromStorage(): string | null {
  if (typeof window === "undefined" || !window.sessionStorage) return null;
  try {
    return window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export const getAccessToken = (): string | null => {
  if (!initialized) {
    cached = loadFromStorage();
    initialized = true;
  }
  return cached;
};

export const setAccessToken = (token: string | null): void => {
  cached = token;
  initialized = true;
  if (typeof window === "undefined" || !window.sessionStorage) return;
  try {
    if (token) {
      window.sessionStorage.setItem(STORAGE_KEY, token);
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // sessionStorage quota / disabled — silently ignore
  }
};
