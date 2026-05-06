import { useCallback, useEffect, useMemo, useState } from "react";
import { getFailedLoginsApi, getFailedLoginsCountApi } from "../api";
import PageLoader from "../components/PageLoader";
import type { FailedLoginAttemptResponse } from "../interfaces";
import { extractErrorMessage } from "../utils/errorMessage";

const REASON_META: Record<string, { label: string; cls: string }> = {
  no_user: {
    label: "Foydalanuvchi topilmadi",
    cls: "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800",
  },
  wrong_password: {
    label: "Parol noto'g'ri",
    cls: "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800",
  },
  inactive: {
    label: "Bloklangan hisob",
    cls: "bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 border-gray-200 dark:border-slate-600",
  },
  locked: {
    label: "Lockout",
    cls: "bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800",
  },
};

function ReasonBadge({ reason }: { reason: string }) {
  const meta = REASON_META[reason] || {
    label: reason,
    cls: "bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-slate-400 border-gray-200 dark:border-slate-700",
  };
  return (
    <span
      className={`inline-block px-2.5 py-1 rounded-lg text-xs font-medium border ${meta.cls}`}
    >
      {meta.label}
    </span>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("uz-UZ", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function shortUA(ua: string | null): string {
  if (!ua) return "—";
  if (ua.length <= 60) return ua;
  return ua.slice(0, 60) + "…";
}

export default function FailedLoginsPage() {
  const [items, setItems] = useState<FailedLoginAttemptResponse[]>([]);
  const [count, setCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [username, setUsername] = useState("");
  const [since, setSince] = useState("");
  const [limit, setLimit] = useState(100);
  const [reasonFilter, setReasonFilter] = useState<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: { username?: string; since?: string; limit?: number } = {
        limit,
      };
      if (username.trim()) params.username = username.trim();
      if (since) {
        // datetime-local → ISO with seconds
        params.since = new Date(since).toISOString();
      }

      const [rows, c] = await Promise.all([
        getFailedLoginsApi(params),
        getFailedLoginsCountApi({
          username: params.username,
          since: params.since,
        }),
      ]);
      setItems(rows);
      setCount(c.count);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [username, since, limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = useMemo(() => {
    if (!reasonFilter) return items;
    return items.filter((i) => i.reason === reasonFilter);
  }, [items, reasonFilter]);

  const reasonCounts = useMemo(() => {
    const map: Record<string, number> = {};
    items.forEach((i) => {
      map[i.reason] = (map[i.reason] || 0) + 1;
    });
    return map;
  }, [items]);

  const handleFilter = () => fetchData();
  const handleReset = () => {
    setUsername("");
    setSince("");
    setReasonFilter("");
    setLimit(100);
  };

  return (
    <div>
      <div className="mb-8">
        <h2 className="section-title">Failed Login Audit</h2>
        <p className="section-subtitle">
          Tizimga kirishda muvaffaqiyatsiz urinishlar (forensic / xavfsizlik tahlili)
        </p>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {error}
          <button
            onClick={() => setError("")}
            className="ml-auto underline text-xs"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="glass-card p-5 mb-5 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="masalan: admin"
            className="input-field !py-2 !text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">
            Vaqtdan boshlab
          </label>
          <input
            type="datetime-local"
            value={since}
            onChange={(e) => setSince(e.target.value)}
            className="input-field !py-2 !text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">
            Limit
          </label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input-field !py-2 !text-sm"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">
            Sabab
          </label>
          <select
            value={reasonFilter}
            onChange={(e) => setReasonFilter(e.target.value)}
            className="input-field !py-2 !text-sm"
          >
            <option value="">Barchasi</option>
            <option value="wrong_password">Parol noto'g'ri</option>
            <option value="no_user">Foydalanuvchi yo'q</option>
            <option value="inactive">Bloklangan</option>
            <option value="locked">Lockout</option>
          </select>
        </div>
        <button onClick={handleFilter} className="btn-primary !py-2 text-sm">
          Filtrlash
        </button>
        {(username || since || reasonFilter || limit !== 100) && (
          <button onClick={handleReset} className="btn-secondary !py-2 text-sm">
            Tozalash
          </button>
        )}
        {count !== null && (
          <span className="text-sm text-gray-500 dark:text-slate-400 ml-auto">
            DB jami: <b>{count}</b> ta
          </span>
        )}
      </div>

      {/* Reason breakdown */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {Object.entries(REASON_META).map(([key, meta]) => (
            <button
              key={key}
              onClick={() => setReasonFilter(reasonFilter === key ? "" : key)}
              className={`glass-card p-4 text-left transition hover:shadow-md ${
                reasonFilter === key ? "ring-2 ring-primary-500" : ""
              }`}
            >
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
                {meta.label}
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {reasonCounts[key] || 0}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <PageLoader />
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">
            Ma'lumot topilmadi
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    ID
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Username
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    IP manzil
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    User-Agent
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Sabab
                  </th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">
                    Vaqt
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition"
                  >
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                      #{row.id}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {row.username || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-slate-300">
                      {row.ip_address}
                    </td>
                    <td
                      className="px-4 py-3 text-xs text-gray-500 dark:text-slate-400 max-w-md"
                      title={row.user_agent || ""}
                    >
                      {shortUA(row.user_agent)}
                    </td>
                    <td className="px-4 py-3">
                      <ReasonBadge reason={row.reason} />
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                      {formatDate(row.attempted_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-gray-400 dark:text-slate-500">
        ⚠ 90 kundan eski yozuvlar avtomatik o'chiriladi (Celery beat).
      </p>
    </div>
  );
}
