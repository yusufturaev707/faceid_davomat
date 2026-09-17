import { useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import { Copy } from "./components/icons";
import { Button, Card, ErrorState, LoadingState, Section } from "./components/ui";
import { AppProvider, regionStorage, resolveInitialRegion, type AppState } from "./context";
import { useAsync } from "./hooks";
import { NavigationProvider, type Route } from "./navigation";
import { CheatScreen } from "./screens/CheatScreen";
import { FaceIdScreen } from "./screens/FaceIdScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { RegionRouteScreen, RegionScreen } from "./screens/RegionScreen";
import { RemoveScreen } from "./screens/RemoveScreen";
import { SessionScreen } from "./screens/SessionScreen";
import { SmenaScreen } from "./screens/SmenaScreen";
import { StatsScreen } from "./screens/StatsScreen";
import { telegram } from "./telegram";
import type { Operator, Region } from "./types";

export function App() {
  if (!telegram.initData) return <NotInTelegram />;
  return <AccessGate />;
}

function AccessGate() {
  const me = useAsync(() => api.me(), []);

  if (me.loading && !me.data) {
    return (
      <FullScreen>
        <LoadingState label="Kirish tekshirilmoqda..." />
      </FullScreen>
    );
  }
  if (me.error) {
    const expired = me.error instanceof ApiError && me.error.status === 401;
    return (
      <FullScreen>
        <ErrorState message={me.error.message} onRetry={expired ? undefined : me.reload} />
        {expired && <Button onClick={() => telegram.close()}>Ilovani yopish</Button>}
      </FullScreen>
    );
  }
  const data = me.data!;
  if (!data.allowed || !data.user) {
    return <AccessDenied telegramId={data.telegram_id} message={data.message} />;
  }
  if (data.user.regions.length === 0) {
    return (
      <FullScreen>
        <ErrorState message="Sizga viloyat biriktirilmagan. Administrator bilan bog'laning." />
      </FullScreen>
    );
  }
  return <OperatorApp operator={data.user} />;
}

function OperatorApp({ operator }: { operator: Operator }) {
  const regions = useMemo(
    () => [...operator.regions].sort((a, b) => a.number - b.number || a.name.localeCompare(b.name)),
    [operator.regions],
  );
  const [region, setRegion] = useState<Region | null>(() =>
    resolveInitialRegion(regions, regionStorage.load(operator.telegram_id)),
  );

  const selectRegion = (regionId: number) => {
    const next = regions.find((r) => r.id === regionId);
    if (!next) return;
    regionStorage.save(operator.telegram_id, next.id);
    setRegion(next);
  };

  if (!region) {
    // 2+ viloyat va tanlov yo'q — ish boshlashdan oldin tanlash majburiy.
    return <RegionScreen regions={regions} currentId={null} onSelect={selectRegion} fio={operator.fio} />;
  }

  const state: AppState = { operator, region, regions, selectRegion };
  return (
    <AppProvider value={state}>
      <NavigationProvider initial={{ name: "home" }}>{renderRoute}</NavigationProvider>
    </AppProvider>
  );
}

function renderRoute(route: Route) {
  switch (route.name) {
    case "home":
      return <HomeScreen />;
    case "regions":
      return <RegionRouteScreen />;
    case "session":
      return <SessionScreen session={route.session} />;
    case "smena":
      return <SmenaScreen session={route.session} smena={route.smena} />;
    case "stats":
      return <StatsScreen session={route.session} scope={route.scope} />;
    case "faceid":
      return <FaceIdScreen session={route.session} smena={route.smena} />;
    case "remove":
      return <RemoveScreen smena={route.smena} />;
    case "cheat":
      return <CheatScreen session={route.session} smena={route.smena} />;
  }
}

function FullScreen({ children }: { children: ReactNode }) {
  return (
    <div className="tg-screen mx-auto flex min-h-[80vh] max-w-xl flex-col justify-center gap-4 px-4">
      {children}
    </div>
  );
}

function NotInTelegram() {
  return (
    <FullScreen>
      <Card className="text-center">
        <p className="text-[18px] font-semibold text-tg-text">Ilovani Telegram orqali oching</p>
        <p className="mt-2 text-[14px] leading-snug text-tg-hint">
          Davomat ilovasi faqat Telegram bot ichida ishlaydi. Botga kirib, «Davomat ilovasini ochish»
          tugmasini bosing.
        </p>
      </Card>
    </FullScreen>
  );
}

function AccessDenied({ telegramId, message }: { telegramId: number; message: string | null }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(String(telegramId));
      setCopied(true);
      telegram.haptic("success");
    } catch {
      setCopied(false);
    }
  };

  return (
    <FullScreen>
      <Card className="text-center">
        <p className="text-[18px] font-semibold text-tg-text">Ruxsat berilmagan</p>
        <p className="mt-2 text-[14px] leading-snug text-tg-hint">
          {message || "Sizga davomat ilovasidan foydalanish ruxsati berilmagan."}
        </p>
      </Card>
      <Section title="Sizning Telegram ID" footer="Shu raqamni administratorga yuboring.">
        <div className="flex items-center gap-3 px-4 py-3">
          <span className="flex-1 select-all font-mono text-[22px] tracking-wider text-tg-text">
            {telegramId}
          </span>
          <button
            type="button"
            onClick={copy}
            className="tg-tint flex h-10 items-center gap-2 rounded-full px-4 text-[14px] font-medium text-tg-button"
          >
            <Copy width={16} height={16} />
            {copied ? "Nusxalandi" : "Nusxalash"}
          </button>
        </div>
      </Section>
    </FullScreen>
  );
}
