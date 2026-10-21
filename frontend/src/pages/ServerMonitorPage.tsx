import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getServerOverviewApi } from "../api";
import HistoryPanel from "../components/monitor/HistoryPanel";
import LogViewer from "../components/monitor/LogViewer";
import {
  formatBytes,
  formatDuration,
  formatNumber,
  formatRate,
  formatTime,
  pctTone,
  sinceSeconds,
  type Tone,
} from "../components/monitor/format";
import type {
  MonitorAlert,
  MonitorProcess,
  MonitorSection,
  MonitorUnit,
  ServerOverview,
} from "../interfaces";
import { extractErrorMessage } from "../utils/errorMessage";

/**
 * Server monitoringi — faqat superadmin (`SuperAdminRoute` + backend
 * `require_super_admin`). Uch bo'lim: umumiy holat (har 15 s yangilanadi),
 * yuklama tarixi (grafiklar) va loglar. Hammasi faqat o'qish uchun.
 */

const OVERVIEW_POLL_MS = 15000;

type Tab = "overview" | "history" | "logs";
const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Umumiy holat" },
  { key: "history", label: "Yuklama tarixi" },
  { key: "logs", label: "Loglar" },
];

// ---------------------------------------------------------------------------
// Kichik bo'laklar
// ---------------------------------------------------------------------------

const TONE_BAR: Record<Tone, string> = {
  ok: "bg-primary-600 dark:bg-primary-500",
  warn: "bg-amber-500",
  crit: "bg-red-600 dark:bg-red-500",
  muted: "bg-gray-300 dark:bg-slate-600",
};

function Meter({ label, pct, detail }: { label: string; pct: number | null; detail?: string }) {
  const tone = pctTone(pct);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-[12.5px]">
        <span className="text-gray-600 dark:text-slate-300 truncate">{label}</span>
        <span className="font-semibold tabular-nums text-gray-900 dark:text-white">
          {pct == null ? "—" : `${pct.toFixed(1)}%`}
          {tone === "crit" && <span className="ml-1 text-red-600 dark:text-red-400">· juda yuqori</span>}
          {tone === "warn" && <span className="ml-1 text-amber-600 dark:text-amber-400">· yuqori</span>}
        </span>
      </div>
      <div className="mt-1.5 h-2 rounded-full bg-gray-100 dark:bg-slate-700/70 overflow-hidden">
        <div
          className={`h-full rounded-full ${TONE_BAR[tone]} transition-[width] duration-500`}
          style={{ width: `${Math.min(100, Math.max(0, pct ?? 0))}%` }}
        />
      </div>
      {detail && <p className="mt-1 text-[11px] text-gray-500 dark:text-slate-400 tabular-nums">{detail}</p>}
    </div>
  );
}

function Card({
  title,
  right,
  children,
  className = "",
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`glass-card p-4 sm:p-5 ${className}`}>
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="text-[14px] font-bold text-gray-900 dark:text-white">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

function SectionError({ section }: { section: MonitorSection<unknown> }) {
  if (section.ok) return null;
  return (
    <p className="text-[12.5px] text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 rounded-lg px-3 py-2">
      Ma'lumot olinmadi: {section.error}
    </p>
  );
}

function Status({ tone, children }: { tone: "ok" | "warn" | "crit" | "muted"; children: React.ReactNode }) {
  const cls = {
    ok: "badge-success",
    warn: "badge-warning",
    crit: "badge-error",
    muted:
      "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-400",
  }[tone];
  const dot = { ok: "bg-emerald-500", warn: "bg-amber-500", crit: "bg-red-500", muted: "bg-gray-400" }[tone];
  return (
    <span className={cls}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {children}
    </span>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5 border-b border-gray-100 dark:border-slate-700/50 last:border-0 text-[12.5px]">
      <span className="text-gray-500 dark:text-slate-400">{k}</span>
      <span className="font-medium text-gray-900 dark:text-slate-100 tabular-nums text-right min-w-0 truncate">{v}</span>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="surface-tonal px-4 py-3">
      <p className="text-[11.5px] text-gray-500 dark:text-slate-400 truncate">{label}</p>
      <p className="text-xl font-bold tabular-nums text-gray-900 dark:text-white mt-0.5">{value}</p>
      {hint && <p className="text-[10.5px] text-gray-400 dark:text-slate-500 mt-0.5">{hint}</p>}
    </div>
  );
}

const th = "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400";
const td = "px-3 py-2 text-[12.5px] text-gray-800 dark:text-slate-200 tabular-nums";

function unitStatus(u: MonitorUnit): { tone: Tone; label: string } {
  if (u.load_state === "not-found") return { tone: "muted", label: "o'rnatilmagan" };
  if (u.active_state === "active") {
    return { tone: "ok", label: u.sub_state === "running" ? "ishlayapti" : `faol (${u.sub_state})` };
  }
  if (u.active_state === "failed") return { tone: "crit", label: "ishdan chiqqan" };
  if (u.active_state === "activating" || u.active_state === "reloading") {
    return { tone: "warn", label: "ishga tushmoqda" };
  }
  return { tone: "crit", label: `to'xtagan (${u.active_state})` };
}

const ALERT_STYLE: Record<MonitorAlert["level"], { box: string; label: string }> = {
  critical: { box: "bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-200 ring-red-200 dark:ring-red-800/60", label: "Jiddiy" },
  warning: { box: "bg-amber-50 text-amber-900 dark:bg-amber-900/25 dark:text-amber-200 ring-amber-200 dark:ring-amber-800/60", label: "Diqqat" },
  info: { box: "bg-sky-50 text-sky-900 dark:bg-sky-900/25 dark:text-sky-200 ring-sky-200 dark:ring-sky-800/60", label: "Ma'lumot" },
};

// ---------------------------------------------------------------------------
// Umumiy holat
// ---------------------------------------------------------------------------

function ProcessTable({ rows }: { rows: MonitorProcess[] }) {
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full min-w-[560px]">
        <thead>
          <tr>
            <th className={th}>PID</th>
            <th className={th}>Jarayon</th>
            <th className={th}>Foydalanuvchi</th>
            <th className={`${th} text-right`}>CPU</th>
            <th className={`${th} text-right`}>RAM</th>
            <th className={`${th} text-right`}>Oqimlar</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
          {rows.map((p) => (
            <tr key={p.pid}>
              <td className={td}>{p.pid}</td>
              <td className={`${td} font-medium`}>
                {p.name}
                {p.group && (
                  <span className="ml-2 text-[10.5px] px-1.5 py-0.5 rounded bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                    FaceID
                  </span>
                )}
              </td>
              <td className={`${td} text-gray-500 dark:text-slate-400`}>{p.user ?? "—"}</td>
              <td className={`${td} text-right`}>{p.cpu_percent.toFixed(1)}%</td>
              <td className={`${td} text-right`}>{formatBytes(p.rss)}</td>
              <td className={`${td} text-right`}>{p.threads}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Overview({ data }: { data: ServerOverview }) {
  const [procSort, setProcSort] = useState<"cpu" | "mem">("cpu");
  const { system, services, database: db, redis, celery, app, activity } = data;
  const appDisk = system.ok ? system.disks.find((d) => d.contains_app) ?? system.disks[0] : undefined;
  const apiGroup = system.ok ? system.groups.find((g) => g.key === "api") : undefined;

  return (
    <div className="space-y-4">
      {/* Ogohlantirishlar */}
      {data.alerts.length > 0 ? (
        <div className="space-y-2">
          {data.alerts.map((a, i) => (
            <div key={i} className={`rounded-xl px-4 py-2.5 text-[13px] ring-1 flex gap-2 ${ALERT_STYLE[a.level].box}`}>
              <span className="font-semibold shrink-0">{ALERT_STYLE[a.level].label}:</span>
              <span>{a.message}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl px-4 py-2.5 text-[13px] ring-1 bg-emerald-50 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/25 dark:text-emerald-200 dark:ring-emerald-800/60">
          Hammasi joyida — muammo aniqlanmadi.
        </div>
      )}

      {/* Resurslar */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card title="Protsessor (CPU)">
          {system.ok ? (
            <div className="space-y-3">
              <Meter
                label={`${system.cpu.cores_logical} yadro (${system.cpu.cores_physical} fizik)`}
                pct={system.cpu.percent}
              />
              <KV k="Load average" v={`${system.cpu.load_1} · ${system.cpu.load_5} · ${system.cpu.load_15}`} />
              <KV k="Chastota" v={system.cpu.freq_mhz ? `${system.cpu.freq_mhz} MHz` : "—"} />
              {system.cpu.temperature_c != null && <KV k="Harorat" v={`${system.cpu.temperature_c} °C`} />}
              <KV k="Jarayonlar" v={formatNumber(system.process_count)} />
            </div>
          ) : (
            <SectionError section={system} />
          )}
        </Card>

        <Card title="Xotira (RAM)">
          {system.ok ? (
            <div className="space-y-3">
              <Meter
                label="RAM"
                pct={system.memory.percent}
                detail={`${formatBytes(system.memory.used)} / ${formatBytes(system.memory.total)} · bo'sh ${formatBytes(system.memory.available)}`}
              />
              <Meter
                label="Swap"
                pct={system.memory.swap_total ? system.memory.swap_percent : null}
                detail={
                  system.memory.swap_total
                    ? `${formatBytes(system.memory.swap_used)} / ${formatBytes(system.memory.swap_total)}`
                    : "Swap yo'q"
                }
              />
              {system.memory.cached > 0 && <KV k="Kesh (cached)" v={formatBytes(system.memory.cached)} />}
            </div>
          ) : (
            <SectionError section={system} />
          )}
        </Card>

        <Card title="Disk">
          {system.ok && appDisk ? (
            <div className="space-y-3">
              {system.disks.map((d) => (
                <Meter
                  key={d.mountpoint}
                  label={`${d.mountpoint}${d.contains_app ? " (ilova)" : ""}`}
                  pct={d.percent}
                  detail={`bo'sh ${formatBytes(d.free)} / ${formatBytes(d.total)}`}
                />
              ))}
              <KV
                k="O'qish / yozish"
                v={`${formatRate(system.disk_io.read_per_sec)} · ${formatRate(system.disk_io.write_per_sec)}`}
              />
            </div>
          ) : (
            <SectionError section={system} />
          )}
        </Card>

        <Card title="Tarmoq">
          {system.ok ? (
            <div>
              <KV k="Kiruvchi" v={formatRate(system.network.recv_per_sec)} />
              <KV k="Chiquvchi" v={formatRate(system.network.sent_per_sec)} />
              <KV
                k="Jami (yuklanganidan beri)"
                v={`↓ ${formatBytes(system.network.bytes_recv)} · ↑ ${formatBytes(system.network.bytes_sent)}`}
              />
              <KV k="TCP ulanishlar (ESTABLISHED)" v={formatNumber(system.network.connections?.ESTABLISHED ?? null)} />
              <KV k="TIME_WAIT" v={formatNumber(system.network.connections?.TIME_WAIT ?? null)} />
              <KV
                k="Xato / tashlangan paketlar"
                v={`${system.network.errin + system.network.errout} / ${system.network.dropin + system.network.dropout}`}
              />
            </div>
          ) : (
            <SectionError section={system} />
          )}
        </Card>
      </div>

      {/* Yuklama — FaceID faolligi */}
      <Card
        title="Tizim yuklamasi"
        right={
          activity.ok ? (
            <span className="text-[11px] text-gray-400 dark:text-slate-500">
              hisoblangan {formatTime(activity.computed_at)}
            </span>
          ) : undefined
        }
      >
        {activity.ok ? (
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
            <Stat label="Face ID kirish" value={formatNumber(activity.face_id_15m)} hint="oxirgi 15 daqiqa" />
            <Stat label="Face ID kirish" value={formatNumber(activity.face_id_1h)} hint="oxirgi 1 soat" />
            <Stat label="Rasm tekshiruvi" value={formatNumber(activity.verify_15m)} hint="oxirgi 15 daqiqa" />
            <Stat label="Rasm tekshiruvi" value={formatNumber(activity.verify_1h)} hint="oxirgi 1 soat" />
            <Stat label="Rasm tekshiruvi" value={formatNumber(activity.verify_24h)} hint="oxirgi 24 soat" />
            <Stat label="Online foydalanuvchi" value={formatNumber(activity.online_users)} />
            <Stat label="Faol test sessiyalari" value={formatNumber(activity.active_sessions)} />
            <Stat label="Xato login urinishlari" value={formatNumber(activity.failed_logins_1h)} hint="oxirgi 1 soat" />
          </div>
        ) : (
          <SectionError section={activity} />
        )}
      </Card>

      {/* FaceID komponentlari */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card title="API (FastAPI)">
          {app.ok ? (
            <div>
              <KV k="Gunicorn jarayonlari" v={apiGroup ? apiGroup.processes : "—"} />
              <KV k="API xotirasi (RSS)" v={apiGroup ? formatBytes(apiGroup.rss) : "—"} />
              <KV k="Ishlamoqda" v={formatDuration(sinceSeconds(apiGroup?.started_at))} />
              <KV
                k="Face model (shu worker)"
                v={app.face_model_ready ? <Status tone="ok">yuklangan</Status> : <Status tone="warn">yuklanmoqda</Status>}
              />
              <KV k="Navbat limiti (verify)" v={app.queue_max_size} />
              <KV k="Embedding oqimlari" v={app.embedding_workers} />
            </div>
          ) : (
            <SectionError section={app} />
          )}
        </Card>

        <Card
          title="PostgreSQL"
          right={db.ok ? <Status tone="ok">{db.latency_ms} ms</Status> : <Status tone="crit">aloqa yo'q</Status>}
        >
          {db.ok ? (
            <div>
              {db.version && <KV k="Versiya" v={db.version} />}
              {db.size_bytes != null && <KV k="Baza hajmi" v={formatBytes(db.size_bytes)} />}
              {db.max_connections != null && (
                <KV k="Ulanishlar" v={`${db.connections_total} / ${db.max_connections}`} />
              )}
              {db.connections_by_state && (
                <KV
                  k="Holat bo'yicha"
                  v={Object.entries(db.connections_by_state)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(", ")}
                />
              )}
              {db.stats && <KV k="Kesh hit" v={db.stats.cache_hit_percent != null ? `${db.stats.cache_hit_percent}%` : "—"} />}
              {db.stats && <KV k="Deadlock" v={formatNumber(db.stats.deadlocks)} />}
              <KV k="Kutilayotgan qulflar" v={db.waiting_locks ?? "—"} />
              {db.pool && <KV k="Pool (shu worker)" v={`${db.pool.checked_out} band / ${db.pool.size}`} />}
            </div>
          ) : (
            <SectionError section={db} />
          )}
        </Card>

        <Card
          title="Redis"
          right={redis.ok ? <Status tone="ok">{redis.latency_ms} ms</Status> : <Status tone="crit">aloqa yo'q</Status>}
        >
          {redis.ok ? (
            <div>
              <KV k="Versiya" v={redis.version} />
              <KV
                k="Xotira"
                v={`${formatBytes(redis.used_memory)}${redis.maxmemory ? ` / ${formatBytes(redis.maxmemory)}` : ""}`}
              />
              <KV k="Klientlar" v={`${redis.connected_clients} (bloklangan ${redis.blocked_clients})`} />
              <KV k="Amallar/s" v={formatNumber(redis.ops_per_sec)} />
              <KV k="Hit" v={redis.hit_percent != null ? `${redis.hit_percent}%` : "—"} />
              <KV k="Kalitlar" v={formatNumber(redis.keys)} />
              <KV k="Ishlamoqda" v={formatDuration(redis.uptime_seconds)} />
            </div>
          ) : (
            <SectionError section={redis} />
          )}
        </Card>

        <Card title="Celery navbatlari">
          {redis.ok ? (
            <div className="space-y-3">
              {Object.entries(redis.queues).map(([q, n]) => (
                <Meter
                  key={q}
                  label={`${q} — ${n} ta kutmoqda`}
                  pct={q === "verify" && redis.queue_limit ? (n * 100) / redis.queue_limit : null}
                  detail={q === "verify" ? `limit ${redis.queue_limit} — oshsa 429` : "limitsiz (rasm saqlash)"}
                />
              ))}
              <KV k="Bajarilayotgan (unacked)" v={redis.unacked} />
            </div>
          ) : (
            <SectionError section={redis} />
          )}
        </Card>
      </div>

      {/* Celery workerlari */}
      <Card title="Celery workerlari">
        {celery.ok ? (
          celery.workers.length === 0 ? (
            <p className="text-[13px] text-red-700 dark:text-red-300">Birorta worker javob bermadi.</p>
          ) : (
            <div className="overflow-x-auto -mx-1">
              <table className="w-full min-w-[720px]">
                <thead>
                  <tr>
                    <th className={th}>Worker</th>
                    <th className={th}>Navbatlar</th>
                    <th className={th}>Pool</th>
                    <th className={`${th} text-right`}>Bajarilgan</th>
                    <th className={th}>Hozir bajarilmoqda</th>
                    <th className={`${th} text-right`}>Ishlamoqda</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                  {celery.workers.map((w) => (
                    <tr key={w.hostname}>
                      <td className={`${td} font-medium`}>{w.hostname}</td>
                      <td className={td}>{w.queues.join(", ") || "—"}</td>
                      <td className={td}>
                        {w.pool ?? "—"} × {w.concurrency ?? "?"}
                      </td>
                      <td className={`${td} text-right`}>{formatNumber(w.processed)}</td>
                      <td className={td}>
                        {w.active.length === 0
                          ? <span className="text-gray-400 dark:text-slate-500">bo'sh</span>
                          : w.active.map((t, i) => (
                              <div key={i} className="truncate max-w-[320px]">
                                {t.name}
                                {t.running_seconds != null && (
                                  <span className="text-gray-500 dark:text-slate-400"> · {formatDuration(t.running_seconds)}</span>
                                )}
                              </div>
                            ))}
                      </td>
                      <td className={`${td} text-right`}>{formatDuration(w.uptime_seconds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          <SectionError section={celery} />
        )}
      </Card>

      {/* Servislar + komponent jarayonlari */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card title="Servislar (systemd)">
          {services.ok ? (
            !services.available ? (
              <p className="text-[13px] text-gray-500 dark:text-slate-400">Bu serverda systemctl yo'q.</p>
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full min-w-[520px]">
                  <thead>
                    <tr>
                      <th className={th}>Unit</th>
                      <th className={th}>Holat</th>
                      <th className={`${th} text-right`}>Ishlamoqda</th>
                      <th className={`${th} text-right`}>Restart</th>
                      <th className={`${th} text-right`}>Xotira</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                    {services.units.map((u) => {
                      const st = unitStatus(u);
                      return (
                        <tr key={u.unit}>
                          <td className={td}>
                            <p className="font-medium">{u.unit.replace(/\.service$/, "")}</p>
                            {u.description && u.load_state !== "not-found" && (
                              <p className="text-[11px] text-gray-500 dark:text-slate-400 truncate max-w-[260px]">
                                {u.description}
                              </p>
                            )}
                          </td>
                          <td className={td}>
                            <Status tone={st.tone}>{st.label}</Status>
                          </td>
                          <td className={`${td} text-right`}>
                            {u.active_state === "active" ? formatDuration(sinceSeconds(u.since)) : "—"}
                          </td>
                          <td className={`${td} text-right`}>{u.restarts ?? "—"}</td>
                          <td className={`${td} text-right`}>{formatBytes(u.memory)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            <SectionError section={services} />
          )}
        </Card>

        <Card title="FaceID komponentlari (jarayonlar)">
          {system.ok ? (
            system.groups.length === 0 ? (
              <p className="text-[13px] text-gray-500 dark:text-slate-400">Komponent jarayonlari topilmadi.</p>
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full min-w-[480px]">
                  <thead>
                    <tr>
                      <th className={th}>Komponent</th>
                      <th className={`${th} text-right`}>Jarayon</th>
                      <th className={`${th} text-right`}>CPU</th>
                      <th className={`${th} text-right`}>RAM</th>
                      <th className={`${th} text-right`}>Ishlamoqda</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                    {system.groups.map((g) => (
                      <tr key={g.key}>
                        <td className={`${td} font-medium`}>{g.label}</td>
                        <td className={`${td} text-right`}>{g.processes}</td>
                        <td className={`${td} text-right`}>{g.cpu_percent.toFixed(1)}%</td>
                        <td className={`${td} text-right`}>{formatBytes(g.rss)}</td>
                        <td className={`${td} text-right`}>{formatDuration(sinceSeconds(g.started_at))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-[11px] text-gray-400 dark:text-slate-500">
                  CPU: 100% = bitta yadro to'liq band. RAM — jarayonlar RSS yig'indisi (umumiy sahifalar takror sanaladi).
                </p>
              </div>
            )
          ) : (
            <SectionError section={system} />
          )}
        </Card>
      </div>

      {/* Eng og'ir jarayonlar */}
      {system.ok && (
        <Card
          title="Eng og'ir jarayonlar"
          right={
            <div className="inline-flex rounded-full bg-gray-100 dark:bg-slate-800 p-0.5">
              {(["cpu", "mem"] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setProcSort(k)}
                  className={`px-3 h-7 rounded-full text-[12px] font-medium ${
                    procSort === k
                      ? "bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm"
                      : "text-gray-600 dark:text-slate-400"
                  }`}
                >
                  {k === "cpu" ? "CPU bo'yicha" : "RAM bo'yicha"}
                </button>
              ))}
            </div>
          }
        >
          <ProcessTable rows={procSort === "cpu" ? system.top_cpu : system.top_memory} />
        </Card>
      )}

      {/* PostgreSQL tafsilotlari */}
      {db.ok && db.dialect === "postgresql" && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card title="Uzoq davom etayotgan so'rovlar (> 5 s)">
            {(db.long_queries ?? []).length === 0 ? (
              <p className="text-[13px] text-gray-500 dark:text-slate-400">Yo'q.</p>
            ) : (
              <div className="space-y-2">
                {db.long_queries!.map((q) => (
                  <div key={q.pid} className="surface-tonal p-3">
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11.5px] text-gray-500 dark:text-slate-400">
                      <span className="font-semibold text-gray-900 dark:text-white">{formatDuration(q.duration_seconds)}</span>
                      <span>pid {q.pid}</span>
                      <span>{q.state}</span>
                      {q.wait && <span>kutmoqda: {q.wait}</span>}
                      {q.application && <span>{q.application}</span>}
                    </div>
                    <pre className="mt-1.5 text-[11.5px] font-mono whitespace-pre-wrap break-all text-gray-800 dark:text-slate-200">
                      {q.query}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card title="Eng katta jadvallar">
            <div className="overflow-x-auto -mx-1">
              <table className="w-full min-w-[420px]">
                <thead>
                  <tr>
                    <th className={th}>Jadval</th>
                    <th className={`${th} text-right`}>Qatorlar</th>
                    <th className={`${th} text-right`}>O'lik qatorlar</th>
                    <th className={`${th} text-right`}>Hajmi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                  {(db.tables ?? []).map((t) => (
                    <tr key={t.name}>
                      <td className={`${td} font-medium`}>{t.name}</td>
                      <td className={`${td} text-right`}>{formatNumber(t.rows)}</td>
                      <td className={`${td} text-right`}>{formatNumber(t.dead_rows)}</td>
                      <td className={`${td} text-right`}>{formatBytes(t.size_bytes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sahifa
// ---------------------------------------------------------------------------

export default function ServerMonitorPage() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "overview") as Tab;
  const [data, setData] = useState<ServerOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [auto, setAuto] = useState(true);
  const inflight = useRef(false);

  const load = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    try {
      setData(await getServerOverviewApi());
      setError(null);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      inflight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab !== "overview") return;
    load();
    if (!auto) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, OVERVIEW_POLL_MS);
    return () => clearInterval(id);
  }, [tab, auto, load]);

  const host = data?.system.ok ? data.system.host : null;
  const critical = data?.alerts.filter((a) => a.level === "critical").length ?? 0;
  const warnings = data?.alerts.filter((a) => a.level === "warning").length ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="section-title flex items-center gap-2">
            Server monitoringi
            {data && (
              <Status tone={critical ? "crit" : warnings ? "warn" : "ok"}>
                {critical ? `${critical} jiddiy muammo` : warnings ? `${warnings} ogohlantirish` : "sog'lom"}
              </Status>
            )}
          </h1>
          <p className="section-subtitle">
            {host
              ? `${host.hostname} · ${host.os} · yadro ${host.kernel} · ishlamoqda ${formatDuration(host.uptime_seconds)}`
              : "Server holati, FaceID komponentlari, yuklama va loglar"}
          </p>
        </div>
        {tab === "overview" && (
          <div className="flex items-center gap-2">
            <span className="text-[11.5px] text-gray-500 dark:text-slate-400 tabular-nums">
              {data ? `yangilandi ${formatTime(data.generated_at)} · ${data.collect_ms} ms` : ""}
            </span>
            <label className="inline-flex items-center gap-2 text-[13px] text-gray-700 dark:text-slate-300 select-none cursor-pointer">
              <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="rounded" />
              Avto ({OVERVIEW_POLL_MS / 1000} s)
            </label>
            <button type="button" className="btn-secondary !h-9 !px-4" onClick={load}>
              Yangilash
            </button>
          </div>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200 dark:border-slate-700" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setParams(t.key === "overview" ? {} : { tab: t.key }, { replace: true })}
            className={`px-4 h-10 -mb-px text-[13.5px] font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary-600 text-primary-700 dark:text-primary-300"
                : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" &&
        (loading && !data ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {error && (
              <div className="rounded-xl px-4 py-3 text-[13px] bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                {error}
              </div>
            )}
            {data && <Overview data={data} />}
          </>
        ))}
      {tab === "history" && <HistoryPanel />}
      {tab === "logs" && <LogViewer />}
    </div>
  );
}
