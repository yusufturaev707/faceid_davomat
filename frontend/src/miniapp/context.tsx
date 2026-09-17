import { createContext, useContext, type ReactNode } from "react";
import type { Operator, Region } from "./types";

/** Tasdiqlangan operator va u ishlayotgan viloyat — barcha so'rovlar shu kesimda. */
export interface AppState {
  operator: Operator;
  region: Region;
  /** Operatorga biriktirilgan viloyatlar (`number` bo'yicha tartiblangan). */
  regions: Region[];
  selectRegion: (regionId: number) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ value, children }: { value: AppState; children: ReactNode }) {
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const state = useContext(AppContext);
  if (!state) throw new Error("useApp AppProvider ichida ishlatilishi kerak");
  return state;
}

const regionKey = (telegramId: number) => `davomat-miniapp:region:${telegramId}`;

/**
 * Tanlangan viloyat qurilmada saqlanadi (bot kanalida u bot xotirasida edi va
 * restartda yo'qolardi). Storage bloklangan WebView'larda jimgina o'tkaziladi.
 */
export const regionStorage = {
  load(telegramId: number): number | null {
    try {
      const raw = window.localStorage.getItem(regionKey(telegramId));
      return raw ? Number(raw) || null : null;
    } catch {
      return null;
    }
  },
  save(telegramId: number, regionId: number): void {
    try {
      window.localStorage.setItem(regionKey(telegramId), String(regionId));
    } catch {
      /* storage mavjud emas — tanlov faqat shu seans uchun */
    }
  },
};

/** Saqlangan tanlov hali ham ruxsat etilgan bo'lsa — o'sha; yagona viloyat — avtomatik. */
export function resolveInitialRegion(regions: Region[], storedId: number | null): Region | null {
  if (regions.length === 1) return regions[0];
  return regions.find((r) => r.id === storedId) ?? null;
}
