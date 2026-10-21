import { useCallback, useEffect, useRef, useState } from "react";
import { downloadLogFileApi, getJournalApi, getLogSourcesApi, tailLogFileApi } from "../../api";
import type { MonitorLogLevel, MonitorLogSources, MonitorLogTail } from "../../interfaces";
import { extractErrorMessage } from "../../utils/errorMessage";
import { formatBytes, formatTime } from "./format";

/**
 * Loglar: `backend/logs` (gunicorn, celery), botlar, nginx fayllari va systemd
 * journal. Server faylni oxiridan o'qiydi va tokenlarni yashirib beradi.
 * Manba qiymati: `file:<key>` yoki `unit:<nomi>`.
 */

const LINE_OPTIONS = [100, 300, 1000, 2000];
const LIVE_POLL_MS = 5000;

function lineTone(line: string): string {
  if (/\b(ERROR|CRITICAL|FATAL|PANIC)\b|\[(error|crit|alert|emerg)\]|Traceback/.test(line)) {
    return "text-red-300";
  }
  if (/\b(WARNING|WARN)\b|\[warn\]/.test(line)) return "text-amber-300";
  if (/\bDEBUG\b/.test(line)) return "text-slate-500";
  return "text-slate-200";
}

function defaultSource(src: MonitorLogSources): string {
  const pick =
    src.files.find((f) => f.key === "backend/error.log" && f.readable) ??
    src.files.find((f) => f.readable);
  if (pick) return `file:${pick.key}`;
  return src.units.length ? `unit:${src.units[0]}` : "";
}

export default function LogViewer() {
  const [sources, setSources] = useState<MonitorLogSources | null>(null);
  const [source, setSource] = useState("");
  const [lines, setLines] = useState(300);
  const [level, setLevel] = useState<MonitorLogLevel>("");
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [live, setLive] = useState(false);
  const [wrap, setWrap] = useState(true);
  const [data, setData] = useState<MonitorLogTail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const stickBottom = useRef(true);
  const inflight = useRef(false);

  const loadSources = useCallback(async () => {
    try {
      const src = await getLogSourcesApi();
      setSources(src);
      setSource((cur) => cur || defaultSource(src));
    } catch (e) {
      setError(extractErrorMessage(e));
    }
  }, []);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const load = useCallback(
    async (silent: boolean) => {
      if (!source || inflight.current) return;
      inflight.current = true;
      if (!silent) setLoading(true);
      try {
        const [kind, name] = [source.slice(0, source.indexOf(":")), source.slice(source.indexOf(":") + 1)];
        const params = { lines, q: query, level };
        const res = kind === "file" ? await tailLogFileApi(name, params) : await getJournalApi(name, params);
        setData(res);
        setError(null);
      } catch (e) {
        setError(extractErrorMessage(e));
        if (!silent) setData(null);
      } finally {
        inflight.current = false;
        if (!silent) setLoading(false);
      }
    },
    [source, lines, query, level],
  );

  useEffect(() => {
    stickBottom.current = true;
    load(false);
  }, [load]);

  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load(true);
    }, LIVE_POLL_MS);
    return () => clearInterval(id);
  }, [live, load]);

  // Yangi qatorlar kelganda — foydalanuvchi pastda turgan bo'lsa, pastga suriladi.
  useEffect(() => {
    const el = boxRef.current;
    if (el && stickBottom.current) el.scrollTop = el.scrollHeight;
  }, [data]);

  const onScroll = () => {
    const el = boxRef.current;
    if (el) stickBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };

  const isFile = source.startsWith("file:");
  const fileKey = isFile ? source.slice(5) : "";
  const fileMeta = sources?.files.find((f) => f.key === fileKey);
  const groups = Array.from(new Set((sources?.files ?? []).map((f) => f.group)));

  const onDownload = async () => {
    setDownloading(true);
    try {
      await downloadLogFileApi(fileKey);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <label className="md:col-span-5 block">
            <span className="block text-[11.5px] font-medium text-gray-500 dark:text-slate-400 mb-1">Manba</span>
            <select
              className="input-field !py-2"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            >
              {!source && <option value="">Log manbai topilmadi</option>}
              {groups.map((g) => (
                <optgroup key={g} label={`Fayllar — ${g}`}>
                  {sources!.files
                    .filter((f) => f.group === g)
                    .map((f) => (
                      <option key={f.key} value={`file:${f.key}`} disabled={!f.readable}>
                        {f.name} · {formatBytes(f.size)}
                        {f.readable ? "" : " · o'qish huquqi yo'q"}
                      </option>
                    ))}
                </optgroup>
              ))}
              {(sources?.units.length ?? 0) > 0 && (
                <optgroup label="systemd journal">
                  {sources!.units.map((u) => (
                    <option key={u} value={`unit:${u}`}>
                      {u}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </label>
          <label className="md:col-span-2 block">
            <span className="block text-[11.5px] font-medium text-gray-500 dark:text-slate-400 mb-1">Daraja</span>
            <select
              className="input-field !py-2"
              value={level}
              onChange={(e) => setLevel(e.target.value as MonitorLogLevel)}
            >
              <option value="">Hammasi</option>
              <option value="warning">Ogohlantirish va xato</option>
              <option value="error">Faqat xatolar</option>
            </select>
          </label>
          <label className="md:col-span-2 block">
            <span className="block text-[11.5px] font-medium text-gray-500 dark:text-slate-400 mb-1">Qatorlar</span>
            <select
              className="input-field !py-2"
              value={lines}
              onChange={(e) => setLines(Number(e.target.value))}
            >
              {LINE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  Oxirgi {n}
                </option>
              ))}
            </select>
          </label>
          <form
            className="md:col-span-3 block"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery(queryInput.trim());
            }}
          >
            <span className="block text-[11.5px] font-medium text-gray-500 dark:text-slate-400 mb-1">Qidirish</span>
            <input
              className="input-field !py-2"
              placeholder="Matn, masalan: 500 yoki Traceback"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              onBlur={() => setQuery(queryInput.trim())}
            />
          </form>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary !h-9 !px-4" onClick={() => load(false)} disabled={loading}>
            {loading ? "Yuklanmoqda…" : "Yangilash"}
          </button>
          <label className="inline-flex items-center gap-2 text-[13px] text-gray-700 dark:text-slate-300 px-2 select-none cursor-pointer">
            <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} className="rounded" />
            Jonli kuzatish ({LIVE_POLL_MS / 1000} s)
          </label>
          <label className="inline-flex items-center gap-2 text-[13px] text-gray-700 dark:text-slate-300 px-2 select-none cursor-pointer">
            <input type="checkbox" checked={wrap} onChange={(e) => setWrap(e.target.checked)} className="rounded" />
            Qatorni o'rash
          </label>
          <button type="button" className="btn-text !h-9" onClick={loadSources}>
            Ro'yxatni yangilash
          </button>
          {isFile && (
            <button
              type="button"
              className="btn-text !h-9 ml-auto"
              onClick={onDownload}
              disabled={downloading || !fileMeta?.readable}
            >
              {downloading ? "Yuklanmoqda…" : "Faylni yuklab olish"}
            </button>
          )}
        </div>

        {fileMeta && (
          <p className="text-[11.5px] text-gray-500 dark:text-slate-400">
            Hajmi {formatBytes(fileMeta.size)} · oxirgi yozuv {formatTime(data?.modified_at ?? fileMeta.modified_at)}
            {data?.scan_limited && " · filtr bilan faylning oxirgi 32 MB qismi ko'rildi"}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-[13px] bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </div>
      )}
      {data?.available === false && (
        <div className="rounded-xl px-4 py-3 text-[13px] bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          Bu serverda journalctl yo'q.
        </div>
      )}
      {data?.error && (
        <div className="rounded-xl px-4 py-3 text-[13px] bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          journalctl: {data.error}
        </div>
      )}

      <div
        ref={boxRef}
        onScroll={onScroll}
        className="rounded-2xl bg-slate-950 ring-1 ring-slate-800 h-[60vh] min-h-[320px] overflow-auto p-3 font-mono text-[12px] leading-[1.55]"
      >
        {data && data.lines.length === 0 && !loading ? (
          <p className="text-slate-500 p-2">Mos qator topilmadi.</p>
        ) : (
          (data?.lines ?? []).map((line, i) => (
            <div
              key={i}
              className={`${lineTone(line)} ${wrap ? "whitespace-pre-wrap break-all" : "whitespace-pre"} hover:bg-white/5 px-1 rounded`}
            >
              {line}
            </div>
          ))
        )}
      </div>
      <p className="text-[11.5px] text-gray-500 dark:text-slate-400">
        {data ? `${data.lines.length} qator` : ""} · token, parol va API kalitlar server tomonida yashiriladi.
        Loglarni o'qish va yuklab olish audit logga yoziladi.
      </p>
    </div>
  );
}
