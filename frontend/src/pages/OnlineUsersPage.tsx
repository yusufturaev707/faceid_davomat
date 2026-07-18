import { useEffect, useRef, useState } from "react";
import { getOnlineUsersApi } from "../api";
import StatsCard from "../components/StatsCard";
import type { OnlineUser, OnlineUsersResponse } from "../interfaces";

/** Har 20 soniyada avtomatik yangilash. */
const ONLINE_POLL_MS = 20000;

/** ISO vaqtni "N daqiqa oldin" ko'rinishida qaytaradi. */
function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return "hozirgina";
  const min = Math.floor(diffSec / 60);
  if (min < 60) return `${min} daqiqa oldin`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `${hours} soat oldin`;
  const days = Math.floor(hours / 24);
  return `${days} kun oldin`;
}

function EmptyText({ label = "Ma'lumot yo'q" }: { label?: string }) {
  return (
    <p className="text-sm text-gray-400 dark:text-slate-500 py-10 text-center">
      {label}
    </p>
  );
}

function MonitorIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
      />
    </svg>
  );
}

function UsersIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    </svg>
  );
}

/**
 * Online foydalanuvchilar sahifasi — hozir aktiv login sessiyasi (refresh
 * token) bor foydalanuvchilar va ularning qurilmalari. Username tanlanganda
 * shu foydalanuvchining qurilmalari (nechta device'dan online ekani)
 * ko'rsatiladi. Ma'lumot har {ONLINE_POLL_MS / 1000} soniyada yangilanadi.
 */
export default function OnlineUsersPage() {
  const [data, setData] = useState<OnlineUsersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async (silent: boolean) => {
      if (!silent) setLoading(true);
      try {
        const res = await getOnlineUsersApi();
        if (cancelled) return;
        setData(res);
        setDenied(false);
      } catch (err) {
        if (cancelled) return;
        const status = (err as { response?: { status?: number } })?.response
          ?.status;
        if (status === 403 || status === 401) setDenied(true);
      } finally {
        if (!cancelled && !silent) setLoading(false);
      }
    };
    load(false);
    pollRef.current = setInterval(() => load(true), ONLINE_POLL_MS);
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const users = data?.users ?? [];
  const selected: OnlineUser | null =
    users.find((u) => u.user_id === selectedId) ??
    (users.length > 0 ? users[0] : null);

  return (
    <div className="space-y-6">
      {/* Sarlavha */}
      <div className="flex items-center gap-3">
        <span className="relative flex w-3 h-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
        </span>
        <div>
          <h1 className="section-title">Online foydalanuvchilar</h1>
          <p className="section-subtitle">
            Hozir aktiv login sessiyasi bor foydalanuvchilar va qurilmalar
            {data ? ` · oxirgi ${data.window_minutes} daqiqa` : ""}
          </p>
        </div>
      </div>

      {/* Ko'rsatkichlar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatsCard
          title="Online foydalanuvchi"
          value={data?.online_users ?? 0}
          color="green"
          icon={<UsersIcon className="w-5 h-5" />}
        />
        <StatsCard
          title="Online qurilma"
          value={data?.online_devices ?? 0}
          color="primary"
          icon={<MonitorIcon className="w-5 h-5" />}
        />
        <StatsCard
          title="Aktiv sessiyali foydalanuvchi"
          value={data?.total_users_with_sessions ?? 0}
          color="purple"
          icon={<UsersIcon className="w-5 h-5" />}
        />
        <StatsCard
          title="Jami qurilma (sessiya)"
          value={data?.total_devices ?? 0}
          color="orange"
          icon={<MonitorIcon className="w-5 h-5" />}
        />
      </div>

      {/* Ro'yxat + tanlangan foydalanuvchi qurilmalari */}
      <div className="glass-card p-4 sm:p-5">
        {loading ? (
          <EmptyText label="Yuklanmoqda…" />
        ) : denied ? (
          <EmptyText label="Bu ma'lumotni ko'rish uchun ruxsat yo'q" />
        ) : users.length === 0 ? (
          <EmptyText label="Hozircha online foydalanuvchi yo'q" />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
            {/* Foydalanuvchilar ro'yxati */}
            <div className="space-y-1.5 max-h-[32rem] overflow-y-auto -mr-1 pr-1">
              {users.map((u) => {
                const active = selected?.user_id === u.user_id;
                return (
                  <button
                    key={u.user_id}
                    type="button"
                    onClick={() => setSelectedId(u.user_id)}
                    className={`w-full flex items-center justify-between gap-3 p-2.5 rounded-xl text-left transition-all ring-1 ${
                      active
                        ? "bg-primary-50 dark:bg-primary-900/25 ring-primary-200/70 dark:ring-primary-700/50"
                        : "bg-gray-50/70 dark:bg-slate-800/40 ring-transparent hover:ring-gray-200 dark:hover:ring-slate-700/60"
                    }`}
                  >
                    <span className="flex items-center gap-2.5 min-w-0">
                      <span
                        className={`relative w-9 h-9 rounded-full flex items-center justify-center shrink-0 font-bold text-[13px] ${
                          u.is_online
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                            : "bg-gray-100 text-gray-500 dark:bg-slate-700/60 dark:text-slate-300"
                        }`}
                      >
                        {u.username.charAt(0).toUpperCase()}
                        {u.is_online && (
                          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900" />
                        )}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-[13px] font-semibold text-gray-900 dark:text-white truncate">
                          {u.username}
                        </span>
                        <span className="block text-[11px] text-gray-400 dark:text-slate-500 truncate">
                          {u.full_name || u.role || "—"}
                        </span>
                      </span>
                    </span>
                    <span className="flex items-center gap-1.5 shrink-0 text-[11px] font-semibold text-gray-500 dark:text-slate-400">
                      <MonitorIcon className="w-3.5 h-3.5" />
                      {u.online_device_count}/{u.device_count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Tanlangan foydalanuvchining qurilmalari */}
            <div className="rounded-xl bg-gray-50/60 dark:bg-slate-800/40 ring-1 ring-gray-100 dark:ring-slate-700/50 p-3.5">
              {selected ? (
                <>
                  <div className="flex items-center justify-between gap-2 mb-3 pb-3 border-b border-gray-100 dark:border-slate-700/50">
                    <div className="min-w-0">
                      <p className="text-[13px] font-bold text-gray-900 dark:text-white truncate">
                        {selected.username}
                      </p>
                      <p className="text-[11px] text-gray-400 dark:text-slate-500">
                        {selected.online_device_count} ta qurilmadan online ·{" "}
                        {selected.device_count} ta sessiya
                      </p>
                    </div>
                    <span
                      className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                        selected.is_online
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                          : "bg-gray-100 text-gray-500 dark:bg-slate-700/50 dark:text-slate-300"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          selected.is_online ? "bg-emerald-500" : "bg-gray-400"
                        }`}
                      />
                      {selected.is_online ? "Online" : "Faolsiz"}
                    </span>
                  </div>
                  <div className="space-y-2 max-h-[28rem] overflow-y-auto -mr-1 pr-1">
                    {selected.devices.map((d, i) => (
                      <div
                        key={d.family_id}
                        className="flex items-center gap-3 rounded-lg bg-white dark:bg-slate-900/50 ring-1 ring-gray-100 dark:ring-slate-700/50 px-3 py-2"
                      >
                        <div
                          className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                            d.is_online
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                              : "bg-gray-100 text-gray-400 dark:bg-slate-700/60 dark:text-slate-400"
                          }`}
                        >
                          <MonitorIcon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-[12.5px] font-semibold text-gray-800 dark:text-slate-100 leading-tight">
                            Qurilma {i + 1}
                            <span className="ml-1.5 text-[10.5px] font-normal text-gray-400 dark:text-slate-500">
                              #{d.family_id.slice(0, 8)}
                            </span>
                          </p>
                          <p className="text-[11px] text-gray-400 dark:text-slate-500">
                            Oxirgi faollik: {relTime(d.last_active)}
                          </p>
                        </div>
                        <span
                          className={`shrink-0 inline-flex items-center gap-1 text-[10.5px] font-bold ${
                            d.is_online
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-gray-400 dark:text-slate-500"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              d.is_online ? "bg-emerald-500" : "bg-gray-400"
                            }`}
                          />
                          {d.is_online ? "online" : "faolsiz"}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <EmptyText label="Foydalanuvchini tanlang" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
