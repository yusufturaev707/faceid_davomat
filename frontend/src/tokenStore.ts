/** Access tokenni memory da saqlash (XSS himoyasi uchun localStorage ishlatilmaydi) */
let accessToken: string | null = null;

export const getAccessToken = () => accessToken;
export const setAccessToken = (token: string | null) => {
  accessToken = token;
};
