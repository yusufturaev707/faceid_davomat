import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { api } from "./api";
import { useToast } from "./components/ui";
import { useApp } from "./context";
import { telegram } from "./telegram";
import type { StatsScope } from "./types";

export interface AsyncState<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
}

/** Ma'lumot yuklash: `deps` o'zgarganda yoki `reload()` da qayta so'raydi. */
export function useAsync<T>(fetcher: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(undefined);
    fetcherRef
      .current()
      .then((result) => {
        if (!alive) return;
        setData(result);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (!alive) return;
        setError(err);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, error, loading, reload };
}

/** Kelmaganlar Excel'ini foydalanuvchi Telegram chatiga yuborish. */
export function useSendAbsentees(sessionId: number, scope: StatsScope) {
  const { region } = useApp();
  const toast = useToast();
  const [sending, setSending] = useState(false);

  const send = useCallback(async () => {
    setSending(true);
    try {
      const result = await api.sendAbsentees(sessionId, scope, region.id);
      if (result.status === "sent") {
        telegram.haptic("success");
        toast(`Chatga yuborildi: ${result.count} ta kelmagan talabgor`, "success");
      } else {
        toast(result.message || "Kelmagan talabgorlar yo'q", "neutral");
      }
    } catch (err) {
      telegram.haptic("error");
      toast((err as Error).message, "destructive");
    } finally {
      setSending(false);
    }
  }, [sessionId, scope, region.id, toast]);

  return { send, sending };
}
