/**
 * Telegram Mini App SDK (`telegram-web-app.js`) ustidagi tiplangan qatlam.
 *
 * SDK `window.Telegram.WebApp` ni har doim yaratadi — hatto oddiy brauzerda ham
 * (bo'sh `initData` bilan). Shuning uchun "Telegram ichidamiz" = `initData`
 * bo'sh emas. Har bir imkoniyat Bot API versiyasiga qarab tekshiriladi: eski
 * klientlarda native tugma/skaner bo'lmasa, UI ilova ichidagi zaxira
 * komponentlarga o'tadi.
 */

type HapticImpact = "light" | "medium" | "heavy" | "rigid" | "soft";
type HapticNotification = "error" | "success" | "warning";

interface BottomButton {
  setParams(params: {
    text?: string;
    color?: string;
    text_color?: string;
    is_active?: boolean;
    is_visible?: boolean;
  }): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; first_name?: string } };
  version: string;
  platform: string;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string | undefined>;
  isVersionAtLeast(version: string): boolean;
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  disableVerticalSwipes?: () => void;
  showScanQrPopup(params: { text?: string }, callback?: (text: string) => boolean | void): void;
  closeScanQrPopup(): void;
  BackButton: {
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  MainButton: BottomButton;
  HapticFeedback: {
    impactOccurred(style: HapticImpact): void;
    notificationOccurred(type: HapticNotification): void;
    selectionChanged(): void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

function webApp(): TelegramWebApp | null {
  const app = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;
  return app && app.initData ? app : null;
}

/**
 * SDK hodisalarni Telegram klientiga yetkaza oladimi: mobil/desktop — webview
 * proxy, Telegram Web — iframe. Lokal brauzerda `#tgWebAppData` bilan ochilganda
 * initData bor, lekin native tugmalarni chizadigan klient yo'q — zaxira UI kerak.
 */
function hasTelegramHost(): boolean {
  // telegram-web-app.js `postEvent` bilan bir xil tartib.
  const w = window as Window & { TelegramWebviewProxy?: unknown; external?: object };
  return (
    w.TelegramWebviewProxy !== undefined ||
    (!!w.external && "notify" in w.external) ||
    w.parent !== w
  );
}

export const telegram = {
  get app(): TelegramWebApp | null {
    return webApp();
  },

  /** Backend auth uchun imzolangan `initData` (Telegram tashqarisida bo'sh). */
  get initData(): string {
    return webApp()?.initData ?? "";
  },

  supports(version: string): boolean {
    return webApp()?.isVersionAtLeast(version) ?? false;
  },

  get hasBackButton(): boolean {
    return hasTelegramHost() && this.supports("6.1");
  },

  get hasMainButton(): boolean {
    return hasTelegramHost() && webApp() !== null;
  },

  /** Native QR skaner faqat mobil klientlarda ishlaydi (Desktop/Web'da yo'q). */
  get canScanQr(): boolean {
    const app = webApp();
    return (
      !!app && hasTelegramHost() && app.isVersionAtLeast("6.4") && ["android", "ios"].includes(app.platform)
    );
  },

  init(): void {
    const app = webApp();
    if (!app) return;
    app.ready();
    app.expand();
    if (app.isVersionAtLeast("6.1")) {
      app.setHeaderColor("secondary_bg_color");
      app.setBackgroundColor("secondary_bg_color");
    }
    // Uzun ro'yxat va formalarni pastga surganda ilova tasodifan yopilmasin.
    if (app.isVersionAtLeast("7.7")) app.disableVerticalSwipes?.();
  },

  haptic(type: HapticNotification): void {
    if (this.supports("6.1")) webApp()?.HapticFeedback.notificationOccurred(type);
  },

  tap(): void {
    if (this.supports("6.1")) webApp()?.HapticFeedback.selectionChanged();
  },

  /**
   * Native QR skanerni ochadi. `onText` true qaytarsa skaner yopiladi; false —
   * noto'g'ri QR, foydalanuvchi skanerlashni davom ettiradi.
   */
  scanQr(hint: string, onText: (text: string) => boolean): void {
    webApp()?.showScanQrPopup({ text: hint }, (text) => onText(text));
  },

  close(): void {
    webApp()?.close();
  },
};
