/**
 * Stack navigatsiya — Telegram BackButton bilan bog'langan.
 *
 * Mini App'da brauzer tarixi ma'nosiz (URL ko'rinmaydi), shuning uchun
 * router o'rniga oddiy stek: `push` — yangi ekran, BackButton — `back`.
 * Ko'p qadamli ekranlar (Face ID, chetlatish) `useBackHandler` orqali
 * BackButton'ni o'zining oldingi qadamiga yo'naltiradi.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ChevronLeft } from "./components/icons";
import { telegram } from "./telegram";
import type { ReadySession, SmenaInfo, StatsScope } from "./types";

export type Route =
  | { name: "home" }
  | { name: "regions" }
  | { name: "session"; session: ReadySession }
  | { name: "smena"; session: ReadySession; smena: SmenaInfo }
  | { name: "stats"; session: ReadySession; scope: StatsScope }
  | { name: "faceid"; session: ReadySession; smena: SmenaInfo }
  | { name: "remove"; session: ReadySession; smena: SmenaInfo }
  | { name: "cheat"; session: ReadySession; smena: SmenaInfo };

type BackHandler = () => boolean;

interface Navigation {
  route: Route;
  depth: number;
  push: (route: Route) => void;
  back: () => void;
  reset: (route: Route) => void;
  setBackHandler: (handler: BackHandler | null) => void;
}

const NavigationContext = createContext<Navigation | null>(null);

export function NavigationProvider({
  initial,
  children,
}: {
  initial: Route;
  children: (route: Route, depth: number) => ReactNode;
}) {
  const [stack, setStack] = useState<Route[]>([initial]);
  const backHandler = useRef<BackHandler | null>(null);

  const push = useCallback((route: Route) => {
    setStack((current) => [...current, route]);
    window.scrollTo(0, 0);
  }, []);

  const back = useCallback(() => {
    if (backHandler.current?.()) return;
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : current));
    window.scrollTo(0, 0);
  }, []);

  const reset = useCallback((route: Route) => {
    setStack([route]);
    window.scrollTo(0, 0);
  }, []);

  const setBackHandler = useCallback((handler: BackHandler | null) => {
    backHandler.current = handler;
  }, []);

  const depth = stack.length;
  const route = stack[depth - 1];

  useEffect(() => {
    const app = telegram.app;
    if (!app || !telegram.hasBackButton) return;
    const onBack = () => back();
    app.BackButton.onClick(onBack);
    return () => app.BackButton.offClick(onBack);
  }, [back]);

  useEffect(() => {
    const app = telegram.app;
    if (!app || !telegram.hasBackButton) return;
    if (depth > 1) app.BackButton.show();
    else app.BackButton.hide();
  }, [depth]);

  const value = useMemo(
    () => ({ route, depth, push, back, reset, setBackHandler }),
    [route, depth, push, back, reset, setBackHandler],
  );

  return (
    <NavigationContext.Provider value={value}>
      {!telegram.hasBackButton && depth > 1 && (
        <div className="mx-auto max-w-xl px-2 pt-2">
          <button
            type="button"
            onClick={back}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-[16px] text-tg-link active:opacity-60"
          >
            <ChevronLeft width={20} height={20} />
            Orqaga
          </button>
        </div>
      )}
      {/* key — bir xil turdagi ekran qayta ochilganda holat yangidan boshlanadi. */}
      <div key={`${depth}:${route.name}`}>{children(route, depth)}</div>
    </NavigationContext.Provider>
  );
}

export function useNavigation(): Navigation {
  const nav = useContext(NavigationContext);
  if (!nav) throw new Error("useNavigation NavigationProvider ichida ishlatilishi kerak");
  return nav;
}

/**
 * Ekran ichidagi qadamlar uchun: handler `true` qaytarsa BackButton shu yerda
 * "yutiladi" (masalan, natija → selfie qadamiga), `false` — ekran yopiladi.
 */
export function useBackHandler(handler: BackHandler): void {
  const { setBackHandler } = useNavigation();
  const ref = useRef(handler);
  ref.current = handler;

  useEffect(() => {
    const wrapped = () => ref.current();
    setBackHandler(wrapped);
    return () => setBackHandler(null);
  }, [setBackHandler]);
}
