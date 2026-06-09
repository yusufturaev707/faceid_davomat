import { useEffect, useMemo, useState } from "react";
import type {
  StatisticBotAdminResponse,
  StatisticBotCreateRequest,
  StatisticBotUpdateRequest,
} from "../interfaces";
import {
  createStatisticBotApi,
  deleteStatisticBotApi,
  getStatisticBotsApi,
  updateStatisticBotApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

const PAGE_SIZE = 20;

// role: 1=Admin, 2=Rahbar, 3=Xodim
const ROLE_OPTIONS = [
  { value: 1, label: "Admin", hint: "Cheklov yo'q — hamma ma'lumot" },
  { value: 2, label: "Rahbar", hint: "To'lov + 2025-yil ma'lumotlari" },
  { value: 3, label: "Xodim", hint: "To'lov va 2025 ko'rinmaydi" },
];

const roleBadgeClass: Record<number, string> = {
  1: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  2: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  3: "bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300",
};

interface FormState {
  fio: string;
  telegram_id: string;
  role: number;
  status: boolean;
}

const EMPTY_FORM: FormState = {
  fio: "",
  telegram_id: "",
  role: 3,
  status: true,
};

export default function StatisticBotsPage() {
  const [bots, setBots] = useState<StatisticBotAdminResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    try {
      const b = await getStatisticBotsApi();
      setBots(b);
    } catch (e: any) {
      setError(extractErrorMessage(e) || "Ma'lumotlarni yuklashda xatolik");
    } finally {
      setLoading(false);
    }
  }

  const openCreate = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setFormError("");
    setShowModal(true);
  };

  const openEdit = (bot: StatisticBotAdminResponse) => {
    setEditId(bot.id);
    setForm({
      fio: bot.fio,
      telegram_id: String(bot.telegram_id),
      role: bot.role,
      status: bot.status,
    });
    setFormError("");
    setShowModal(true);
  };

  async function handleSave() {
    setFormError("");

    if (!form.fio.trim() || form.fio.trim().length < 2) {
      setFormError("FIO kamida 2 belgi bo'lishi kerak");
      return;
    }
    const tgId = Number(form.telegram_id);
    if (!Number.isInteger(tgId) || tgId <= 0) {
      setFormError("Telegram ID musbat butun son bo'lishi kerak");
      return;
    }
    if (![1, 2, 3].includes(form.role)) {
      setFormError("Rol tanlanishi kerak");
      return;
    }

    setSaving(true);
    try {
      if (editId !== null) {
        const body: StatisticBotUpdateRequest = {
          fio: form.fio.trim(),
          telegram_id: tgId,
          role: form.role,
          status: form.status,
        };
        await updateStatisticBotApi(editId, body);
      } else {
        const body: StatisticBotCreateRequest = {
          fio: form.fio.trim(),
          telegram_id: tgId,
          role: form.role,
          status: form.status,
        };
        await createStatisticBotApi(body);
      }
      setShowModal(false);
      await loadAll();
    } catch (e: any) {
      setFormError(extractErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Bu bot foydalanuvchisini o'chirmoqchimisiz?")) return;
    try {
      await deleteStatisticBotApi(id);
      await loadAll();
    } catch (e: any) {
      setError(extractErrorMessage(e));
    }
  };

  const filteredBots = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return bots;
    return bots.filter(
      (b) =>
        b.fio.toLowerCase().includes(q) ||
        String(b.telegram_id).includes(q) ||
        b.role_name.toLowerCase().includes(q),
    );
  }, [bots, search]);

  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(filteredBots.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [search]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pagedBots = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredBots.slice(start, start + PAGE_SIZE);
  }, [filteredBots, page]);

  if (loading) return <PageLoader />;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Statistika bot foydalanuvchilari</h2>
          <p className="section-subtitle">
            Telegram statistika bot orqali qabul ko'rsatkichlarini ko'ruvchilarni
            boshqarish
          </p>
        </div>
        <PermissionGate permission={PERM.STATISTIC_BOT_CREATE}>
          <button
            onClick={openCreate}
            className="btn-primary flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            Yangi foydalanuvchi
          </button>
        </PermissionGate>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-auto underline text-xs"
          >
            Yopish
          </button>
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Qidirish (FIO, telegram ID, rol)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field w-full max-w-md"
        />
      </div>

      {/* Bots table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 dark:border-slate-700">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                ID
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                FIO
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Telegram ID
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Rol
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Holat
              </th>
              <th className="text-center px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Amallar
              </th>
            </tr>
          </thead>
          <tbody>
            {pagedBots.map((bot) => (
              <tr
                key={bot.id}
                className="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors"
              >
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-slate-400">
                  {bot.id}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-sky-100 dark:bg-sky-900/30 flex items-center justify-center">
                      <span className="text-xs font-bold text-sky-700 dark:text-sky-400">
                        {bot.fio.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {bot.fio}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300 font-mono">
                  {bot.telegram_id}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      roleBadgeClass[bot.role] ?? roleBadgeClass[3]
                    }`}
                  >
                    {bot.role_name}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                      bot.status
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        bot.status ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    {bot.status ? "Faol" : "Bloklangan"}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <PermissionGate permission={PERM.STATISTIC_BOT_UPDATE}>
                      <button
                        onClick={() => openEdit(bot)}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        title="Tahrirlash"
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                    </PermissionGate>
                    <PermissionGate permission={PERM.STATISTIC_BOT_DELETE}>
                      <button
                        onClick={() => handleDelete(bot.id)}
                        className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                        title="O'chirish"
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </PermissionGate>
                  </div>
                </td>
              </tr>
            ))}
            {filteredBots.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-gray-400 dark:text-slate-500"
                >
                  Bot foydalanuvchisi topilmadi
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pages={totalPages} onPageChange={setPage} />

      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500">
        Jami: {filteredBots.length} ta foydalanuvchi
      </p>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editId !== null
                  ? "Foydalanuvchini tahrirlash"
                  : "Yangi foydalanuvchi"}
              </h3>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                Statistika bot orqali qabul ko'rsatkichlarini ko'ruvchi
              </p>
            </div>

            <div className="px-6 py-5 overflow-y-auto flex-1">
              {formError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                  {formError}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    FIO *
                  </label>
                  <input
                    type="text"
                    value={form.fio}
                    onChange={(e) => setForm({ ...form, fio: e.target.value })}
                    className="input-field w-full"
                    placeholder="Familiya Ism Otasining ismi"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    Telegram ID *
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={form.telegram_id}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        telegram_id: e.target.value.replace(/\D/g, ""),
                      })
                    }
                    className="input-field w-full font-mono"
                    placeholder="123456789"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    Rol *
                  </label>
                  <select
                    value={form.role}
                    onChange={(e) =>
                      setForm({ ...form, role: Number(e.target.value) })
                    }
                    className="input-field w-full"
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label} — {r.hint}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1.5 text-[11px] text-gray-500 dark:text-slate-400">
                    {ROLE_OPTIONS.find((r) => r.value === form.role)?.hint}
                  </p>
                </div>

                <div>
                  <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={form.status}
                      onChange={(e) =>
                        setForm({ ...form, status: e.target.checked })
                      }
                      className="rounded h-4 w-4"
                    />
                    <span className="text-sm text-gray-700 dark:text-slate-300">
                      Faol (status)
                    </span>
                  </label>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 dark:border-slate-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowModal(false);
                  setFormError("");
                }}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
