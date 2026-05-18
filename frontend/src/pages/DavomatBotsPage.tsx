import { useEffect, useMemo, useState } from "react";
import type {
  DavomatBotAdminResponse,
  DavomatBotCreateRequest,
  DavomatBotUpdateRequest,
  LookupRegionResponse,
  LookupRoleResponse,
} from "../interfaces";
import {
  createDavomatBotApi,
  deleteDavomatBotApi,
  getDavomatBotsApi,
  getRegionsListApi,
  getRolesListApi,
  updateDavomatBotApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

// `roles.key == 4` → faqat 1 region biriktirilishi mumkin (backend bilan
// teng sertkasiya). Boshqa kalit qiymatlari uchun 1+ region.
const SINGLE_REGION_ROLE_KEY = 4;

interface FormState {
  fio: string;
  telegram_id: string;
  role_id: number | null;
  is_active: boolean;
  region_ids: number[];
}

const EMPTY_FORM: FormState = {
  fio: "",
  telegram_id: "",
  role_id: null,
  is_active: true,
  region_ids: [],
};

export default function DavomatBotsPage() {
  const [bots, setBots] = useState<DavomatBotAdminResponse[]>([]);
  const [roles, setRoles] = useState<LookupRoleResponse[]>([]);
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [regionSearch, setRegionSearch] = useState("");

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    try {
      const [b, r, rg] = await Promise.all([
        getDavomatBotsApi(),
        getRolesListApi(),
        getRegionsListApi(),
      ]);
      setBots(b);
      setRoles(r);
      setRegions(rg);
    } catch (e: any) {
      setError(extractErrorMessage(e) || "Ma'lumotlarni yuklashda xatolik");
    } finally {
      setLoading(false);
    }
  }

  const rolesById = useMemo(() => {
    const map = new Map<number, LookupRoleResponse>();
    for (const r of roles) map.set(r.id, r);
    return map;
  }, [roles]);

  const selectedRole = form.role_id ? rolesById.get(form.role_id) : null;
  const isSingleRegionRole =
    !!selectedRole && selectedRole.key === SINGLE_REGION_ROLE_KEY;

  // Region tanlovi rol qoidasiga rioya qilishi uchun "single" rolda
  // checkbox o'rniga radio kabi ishlaydi (faqat 1 ta tanlangan).
  const toggleRegion = (regionId: number) => {
    setForm((prev) => {
      if (isSingleRegionRole) {
        return { ...prev, region_ids: [regionId] };
      }
      const has = prev.region_ids.includes(regionId);
      const next = has
        ? prev.region_ids.filter((id) => id !== regionId)
        : [...prev.region_ids, regionId];
      return { ...prev, region_ids: next };
    });
  };

  const handleRoleChange = (newRoleId: number | null) => {
    setForm((prev) => {
      const newRole = newRoleId ? rolesById.get(newRoleId) : null;
      // Agar yangi rol single bo'lsa va > 1 region tanlangan bo'lsa,
      // birinchi tanlanganini saqlab qolamiz.
      let newRegions = prev.region_ids;
      if (newRole?.key === SINGLE_REGION_ROLE_KEY && newRegions.length > 1) {
        newRegions = newRegions.slice(0, 1);
      }
      return { ...prev, role_id: newRoleId, region_ids: newRegions };
    });
  };

  const openCreate = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setFormError("");
    setRegionSearch("");
    setShowModal(true);
  };

  const openEdit = (bot: DavomatBotAdminResponse) => {
    setEditId(bot.id);
    setForm({
      fio: bot.fio,
      telegram_id: String(bot.telegram_id),
      role_id: bot.role_id,
      is_active: bot.is_active,
      region_ids: [...bot.region_ids],
    });
    setFormError("");
    setRegionSearch("");
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
    if (form.region_ids.length === 0) {
      setFormError("Kamida 1 ta region tanlanishi shart");
      return;
    }
    if (isSingleRegionRole && form.region_ids.length !== 1) {
      setFormError(
        "Tanlangan rol uchun faqat 1 ta region biriktirilishi mumkin",
      );
      return;
    }

    setSaving(true);
    try {
      if (editId !== null) {
        const body: DavomatBotUpdateRequest = {
          fio: form.fio.trim(),
          telegram_id: tgId,
          role_id: form.role_id,
          is_active: form.is_active,
          region_ids: form.region_ids,
        };
        await updateDavomatBotApi(editId, body);
      } else {
        const body: DavomatBotCreateRequest = {
          fio: form.fio.trim(),
          telegram_id: tgId,
          role_id: form.role_id,
          is_active: form.is_active,
          region_ids: form.region_ids,
        };
        await createDavomatBotApi(body);
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
      await deleteDavomatBotApi(id);
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
        (b.role || "").toLowerCase().includes(q) ||
        b.regions.some((r) => r.name.toLowerCase().includes(q)),
    );
  }, [bots, search]);

  const filteredRegions = useMemo(() => {
    const q = regionSearch.trim().toLowerCase();
    const sorted = [...regions].sort(
      (a, b) => (a.number || 0) - (b.number || 0),
    );
    if (!q) return sorted;
    return sorted.filter((r) => r.name.toLowerCase().includes(q));
  }, [regions, regionSearch]);

  if (loading) return <PageLoader />;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Davomat bot foydalanuvchilari</h2>
          <p className="section-subtitle">
            Telegram bot orqali davomat oluvchi foydalanuvchilarni boshqarish
          </p>
        </div>
        <PermissionGate permission={PERM.DAVOMAT_BOT_CREATE}>
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
            Yangi bot foydalanuvchisi
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
          placeholder="Qidirish (FIO, telegram ID, rol, region)..."
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
                Regionlar
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
            {filteredBots.map((bot) => (
              <tr
                key={bot.id}
                className="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors"
              >
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-slate-400">
                  {bot.id}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                      <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400">
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
                  {bot.role ? (
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        bot.role_key === SINGLE_REGION_ROLE_KEY
                          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                          : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      }`}
                      title={
                        bot.role_key === SINGLE_REGION_ROLE_KEY
                          ? "Faqat 1 region biriktirilishi mumkin"
                          : "Bir nechta region biriktirilishi mumkin"
                      }
                    >
                      {bot.role}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {bot.regions.length === 0 ? (
                    <span className="text-xs text-gray-400">— biriktirilmagan —</span>
                  ) : (
                    <div className="flex flex-wrap gap-1.5 max-w-md">
                      {bot.regions.slice(0, 3).map((r) => (
                        <span
                          key={r.id}
                          className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 border border-emerald-200/50 dark:border-emerald-800/40"
                        >
                          {r.name}
                        </span>
                      ))}
                      {bot.regions.length > 3 && (
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300"
                          title={bot.regions
                            .slice(3)
                            .map((r) => r.name)
                            .join(", ")}
                        >
                          +{bot.regions.length - 3} ko'proq
                        </span>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                      bot.is_active
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        bot.is_active ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    {bot.is_active ? "Faol" : "Bloklangan"}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <PermissionGate permission={PERM.DAVOMAT_BOT_UPDATE}>
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
                    <PermissionGate permission={PERM.DAVOMAT_BOT_DELETE}>
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
                  colSpan={7}
                  className="px-6 py-12 text-center text-gray-400 dark:text-slate-500"
                >
                  Bot foydalanuvchisi topilmadi
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500">
        Jami: {filteredBots.length} ta foydalanuvchi
      </p>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editId !== null
                  ? "Bot foydalanuvchisini tahrirlash"
                  : "Yangi bot foydalanuvchisi"}
              </h3>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                Telegram bot orqali davomat boshqaruvi uchun foydalanuvchi
              </p>
            </div>

            <div className="px-6 py-5 overflow-y-auto flex-1">
              {formError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    FIO *
                  </label>
                  <input
                    type="text"
                    value={form.fio}
                    onChange={(e) =>
                      setForm({ ...form, fio: e.target.value })
                    }
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
                    Rol
                  </label>
                  <select
                    value={form.role_id ?? ""}
                    onChange={(e) =>
                      handleRoleChange(
                        e.target.value ? Number(e.target.value) : null,
                      )
                    }
                    className="input-field w-full"
                  >
                    <option value="">— Tanlanmagan —</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                        {r.key === SINGLE_REGION_ROLE_KEY
                          ? " (bir region)"
                          : ""}
                      </option>
                    ))}
                  </select>
                  {selectedRole && (
                    <p className="mt-1.5 text-[11px] text-gray-500 dark:text-slate-400">
                      {isSingleRegionRole
                        ? "Bu rolda faqat 1 ta region biriktirilishi mumkin."
                        : "Bu rolda 1 yoki bir nechta region biriktirilishi mumkin."}
                    </p>
                  )}
                </div>

                <div className="flex items-end pb-1.5">
                  <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={form.is_active}
                      onChange={(e) =>
                        setForm({ ...form, is_active: e.target.checked })
                      }
                      className="rounded h-4 w-4"
                    />
                    <span className="text-sm text-gray-700 dark:text-slate-300">
                      Faol
                    </span>
                  </label>
                </div>
              </div>

              {/* Region multi-select */}
              <div className="mt-6">
                <div className="flex items-baseline justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                    Regionlar *{" "}
                    <span className="text-xs font-normal text-gray-500 dark:text-slate-400">
                      ({form.region_ids.length} ta tanlandi)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={regionSearch}
                    onChange={(e) => setRegionSearch(e.target.value)}
                    placeholder="Region qidirish..."
                    className="input-field text-xs w-44 py-1.5"
                  />
                </div>

                {isSingleRegionRole && form.region_ids.length > 1 && (
                  <div className="mb-2 text-xs text-amber-600 dark:text-amber-400">
                    Bu rol uchun faqat 1 ta region tanlanadi — boshqasini bossangiz
                    avvalgisi almashtiriladi.
                  </div>
                )}

                <div className="border border-gray-200 dark:border-slate-700 rounded-xl max-h-72 overflow-y-auto bg-gray-50/50 dark:bg-slate-900/30">
                  {filteredRegions.length === 0 ? (
                    <p className="p-4 text-sm text-gray-500 dark:text-slate-400 text-center">
                      Region topilmadi
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 p-2">
                      {filteredRegions.map((r) => {
                        const selected = form.region_ids.includes(r.id);
                        return (
                          <label
                            key={r.id}
                            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm ${
                              selected
                                ? "bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-300 dark:border-emerald-700"
                                : "bg-white dark:bg-slate-800 border border-transparent hover:bg-gray-100 dark:hover:bg-slate-700/50"
                            }`}
                          >
                            <input
                              type={isSingleRegionRole ? "radio" : "checkbox"}
                              name={isSingleRegionRole ? "region-radio" : undefined}
                              checked={selected}
                              onChange={() => toggleRegion(r.id)}
                              className="h-4 w-4"
                            />
                            <span className="flex-1 text-gray-800 dark:text-slate-200">
                              {r.name}
                            </span>
                            <span className="text-[11px] text-gray-400 dark:text-slate-500 font-mono">
                              #{r.number}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Bulk actions — faqat multi-rolda */}
                {!isSingleRegionRole && filteredRegions.length > 0 && (
                  <div className="mt-2 flex items-center gap-3 text-xs">
                    <button
                      type="button"
                      onClick={() =>
                        setForm({
                          ...form,
                          region_ids: filteredRegions.map((r) => r.id),
                        })
                      }
                      className="text-emerald-600 dark:text-emerald-400 hover:underline"
                    >
                      Hammasini tanlash
                    </button>
                    <span className="text-gray-300 dark:text-slate-600">|</span>
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, region_ids: [] })}
                      className="text-red-500 dark:text-red-400 hover:underline"
                    >
                      Tanlovni tozalash
                    </button>
                  </div>
                )}
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
