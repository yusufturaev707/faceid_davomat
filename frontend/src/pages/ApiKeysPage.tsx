import { useCallback, useEffect, useState } from "react";
import type { ApiKeyCreateResponse, ApiKeyResponse } from "../interfaces";
import { createApiKeyApi, getApiKeysApi, revokeApiKeyApi } from "../api";
import PageLoader from "../components/PageLoader";
import { extractErrorMessage } from "../utils/errorMessage";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const fetchKeys = useCallback(async () => {
    try {
      const data = await getApiKeysApi();
      setKeys(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const created = await createApiKeyApi({ name: name.trim() });
      setNewKey(created);
      setName("");
      fetchKeys();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    try {
      await revokeApiKeyApi(keyId);
      fetchKeys();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title">API kalitlar</h1>
        <p className="section-subtitle">
          Tashqi tizimlar uchun API kalitlarni boshqarish
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          {error}
          <button onClick={() => setError("")} className="ml-auto underline text-xs">Yopish</button>
        </div>
      )}

      {/* Yangi kalit yaratish */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Yangi kalit yaratish
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="Kalit nomi (masalan: Tashqi tizim)"
            className="input-field flex-1"
            maxLength={100}
          />
          <button
            onClick={handleCreate}
            disabled={creating || !name.trim()}
            className="btn-primary whitespace-nowrap"
          >
            {creating ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 spinner" />
                Yaratilmoqda...
              </span>
            ) : (
              "Yaratish"
            )}
          </button>
        </div>
      </div>

      {/* Yangi yaratilgan kalit — faqat bir marta ko'rsatiladi */}
      {newKey && (
        <div className="glass-card p-6 border-2 !border-amber-400 dark:!border-amber-500">
          <div className="flex items-start gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-semibold text-amber-800 dark:text-amber-300">
                API kalit yaratildi — bu kalitni saqlang!
              </h3>
              <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
                Bu kalit faqat bir marta ko'rsatiladi. Sahifani yangilasangiz boshqa ko'ra olmaysiz.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <code className="flex-1 px-4 py-3 bg-gray-900 dark:bg-slate-950 text-emerald-400 rounded-xl text-sm font-mono break-all select-all">
              {newKey.raw_key}
            </code>
            <button
              onClick={() => handleCopy(newKey.raw_key)}
              className="btn-secondary flex-shrink-0"
            >
              {copied ? (
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Nusxalandi
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  Nusxalash
                </span>
              )}
            </button>
          </div>

          <button
            onClick={() => setNewKey(null)}
            className="mt-3 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Kalitlar ro'yxati */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <PageLoader />
        ) : keys.length === 0 ? (
          <div className="text-center py-12 text-gray-400 dark:text-slate-500">
            API kalitlar mavjud emas
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50">
                  <th className="text-left px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Nomi</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Kalit (prefix)</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Holat</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Oxirgi ishlatilgan</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Yaratilgan</th>
                  <th className="text-right px-5 py-3 font-medium text-gray-500 dark:text-slate-400">Amal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {keys.map((key) => (
                  <tr key={key.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900 dark:text-white">
                      {key.name}
                    </td>
                    <td className="px-5 py-3.5">
                      <code className="px-2 py-1 bg-gray-100 dark:bg-slate-700 rounded text-xs font-mono text-gray-600 dark:text-slate-300">
                        {key.prefix}...
                      </code>
                    </td>
                    <td className="px-5 py-3.5">
                      {key.is_active ? (
                        <span className="badge-success">Faol</span>
                      ) : (
                        <span className="badge-error">Bekor qilingan</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 dark:text-slate-400">
                      {key.last_used_at
                        ? new Date(key.last_used_at).toLocaleString("uz-UZ")
                        : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 dark:text-slate-400">
                      {new Date(key.created_at).toLocaleString("uz-UZ")}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {key.is_active && (
                        <button
                          onClick={() => handleRevoke(key.id)}
                          className="text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 text-sm font-medium transition-colors"
                        >
                          Bekor qilish
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
