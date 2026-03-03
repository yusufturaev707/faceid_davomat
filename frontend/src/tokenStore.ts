/** Access tokenni memory da saqlash (XSS himoyasi uchun localStorage ishlatilmaydi) */
let accessToken: string | null = null;

export const getAccessToken = () => accessToken;
export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

/** Refresh tokenni localStorage da saqlash */
const REFRESH_KEY = "faceid_refresh_token";

export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);
export const setRefreshToken = (token: string | null) => {
  if (token) {
    localStorage.setItem(REFRESH_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_KEY);
  }
};
