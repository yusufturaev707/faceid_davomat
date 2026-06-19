import { useEffect, useMemo, useState } from "react";
import { extractErrorMessage } from "../utils/errorMessage";
import PermissionGate from "./PermissionGate";
import Pagination from "./Pagination";
import Md3Select from "./Md3Select";

const PAGE_SIZE = 20;

/**
 * Universal CRUD page component for lookup/reference tables.
 *
 * Usage:
 *   <LookupCrudPage
 *     title="Testlar"
 *     subtitle="Test nomlari ro'yxati"
 *     columns={[
 *       { key: "id", label: "ID" },
 *       { key: "name", label: "Nomi" },
 *       { key: "key", label: "Kalit" },
 *     ]}
 *     formFields={[
 *       { key: "name", label: "Nomi", type: "text", required: true },
 *       { key: "key", label: "Kalit", type: "number", required: true },
 *     ]}
 *     fetchAll={getTestsListApi}
 *     createItem={createTestApi}
 *     updateItem={updateTestApi}
 *     deleteItem={deleteTestApi}
 *   />
 */

export interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => React.ReactNode;
}

export interface FormField {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  required?: boolean;
  placeholder?: string;
  options?: { value: string | number; label: string }[];
}

interface Props<T extends { id: number }> {
  title: string;
  subtitle: string;
  columns: Column[];
  formFields: FormField[];
  fetchAll: () => Promise<T[]>;
  createItem: (data: any) => Promise<T>;
  updateItem: (id: number, data: any) => Promise<T>;
  deleteItem: (id: number) => Promise<void>;
  /** Permission codenames — if set, action buttons will be hidden when user lacks permission. */
  createPermission?: string;
  updatePermission?: string;
  deletePermission?: string;
  /** If set, shows a search input that filters client-side on these item keys
   *  (case-insensitive substring match). Pagination + total auto-update. */
  searchKeys?: string[];
  searchPlaceholder?: string;
}

export default function LookupCrudPage<T extends { id: number; is_active?: boolean }>({
  title,
  subtitle,
  columns,
  formFields,
  fetchAll,
  createItem,
  updateItem,
  deleteItem,
  createPermission,
  updatePermission,
  deletePermission,
  searchKeys,
  searchPlaceholder,
}: Props<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Search — faqat `searchKeys` prop berilgan sahifalarda yoqiladi.
  // Client-side filter: lookup ro'yxatlari odatda kichik (1k atrofida),
  // shuning uchun debounce yoki backend search shart emas.
  const [search, setSearch] = useState("");

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState<T | null>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // Pagination (client-side — backend lookup endpointlari hozir paginatsiyani
  // qo'llab-quvvatlamaydi, ro'yxat odatda kichik).
  const [page, setPage] = useState(1);

  useEffect(() => {
    load();
  }, []);

  const filteredItems = useMemo(() => {
    if (!searchKeys || searchKeys.length === 0) return items;
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) =>
      searchKeys.some((k) => {
        const val = (it as any)[k];
        return val != null && String(val).toLowerCase().includes(q);
      }),
    );
  }, [items, search, searchKeys]);

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  // Search o'zgarganda sahifa 1 ga qaytadi — natija ko'rinmay qolmasligi uchun.
  useEffect(() => {
    setPage(1);
  }, [search]);

  const pagedItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredItems.slice(start, start + PAGE_SIZE);
  }, [filteredItems, page]);

  async function load() {
    try {
      const data = await fetchAll();
      setItems(data);
    } catch {
      setError("Ma'lumotlarni yuklashda xatolik. Sahifani yangilang");
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    const initial: Record<string, any> = {};
    formFields.forEach((f) => {
      initial[f.key] = f.type === "number" ? "" : "";
    });
    setForm(initial);
    setEditingItem(null);
    setFormError("");
    setShowModal(true);
  }

  function openEdit(item: T) {
    const values: Record<string, any> = {};
    formFields.forEach((f) => {
      values[f.key] = (item as any)[f.key] ?? "";
    });
    setForm(values);
    setEditingItem(item);
    setFormError("");
    setShowModal(true);
  }

  async function handleSave() {
    // Validate required fields
    for (const f of formFields) {
      if (f.required && (form[f.key] === "" || form[f.key] === undefined || form[f.key] === null)) {
        setFormError(`${f.label} majburiy`);
        return;
      }
    }

    setSaving(true);
    setFormError("");
    try {
      const payload: Record<string, any> = {};
      formFields.forEach((f) => {
        const val = form[f.key];
        if (f.type === "number") {
          payload[f.key] = val === "" ? undefined : Number(val);
        } else {
          payload[f.key] = val;
        }
      });

      if (editingItem) {
        await updateItem(editingItem.id, payload);
      } else {
        await createItem(payload);
      }
      setShowModal(false);
      await load();
    } catch (err: any) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteItem(id);
      setDeleteId(null);
      await load();
    } catch (err: any) {
      setError(extractErrorMessage(err));
      setDeleteId(null);
    }
  }

  async function toggleActive(item: T) {
    try {
      await updateItem(item.id, { is_active: !(item as any).is_active });
      await load();
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="min-w-0">
          <h2 className="section-title">{title}</h2>
          <p className="section-subtitle">{subtitle}</p>
        </div>
        <PermissionGate permission={createPermission}>
          <button onClick={openCreate} className="btn-primary self-start sm:self-auto">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Qo'shish
          </button>
        </PermissionGate>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm flex items-start justify-between gap-3">
          <span>{error}</span>
          <button onClick={() => setError("")} className="underline shrink-0">Yopish</button>
        </div>
      )}

      {/* Search */}
      {searchKeys && searchKeys.length > 0 && (
        <div className="mb-4">
          <div className="relative max-w-md">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder || "Qidirish..."}
              className="input-field !py-2 !pl-9 !text-sm w-full"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
                title="Tozalash"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
        <table className="w-full min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-100 dark:border-slate-700">
              {columns.map((col) => (
                <th key={col.key} className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {col.label}
                </th>
              ))}
              {items.some((i) => "is_active" in i) && (
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  Holat
                </th>
              )}
              <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Amallar
              </th>
            </tr>
          </thead>
          <tbody>
            {pagedItems.map((item) => (
              <tr key={item.id} className="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                {columns.map((col) => (
                  <td key={col.key} className="px-5 py-3.5 text-sm text-gray-700 dark:text-slate-300">
                    {col.render ? col.render((item as any)[col.key], item) : String((item as any)[col.key] ?? "—")}
                  </td>
                ))}
                {"is_active" in item && (
                  <td className="px-5 py-3.5">
                    <PermissionGate
                      permission={updatePermission}
                      fallback={
                        <span
                          className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${
                            (item as any).is_active
                              ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                              : "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${(item as any).is_active ? "bg-green-500" : "bg-red-500"}`} />
                          {(item as any).is_active ? "Faol" : "Nofaol"}
                        </span>
                      }
                    >
                      <button
                        onClick={() => toggleActive(item)}
                        className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full transition-colors ${
                          (item as any).is_active
                            ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30"
                            : "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30"
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${(item as any).is_active ? "bg-green-500" : "bg-red-500"}`} />
                        {(item as any).is_active ? "Faol" : "Nofaol"}
                      </button>
                    </PermissionGate>
                  </td>
                )}
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <PermissionGate permission={updatePermission}>
                      <button
                        onClick={() => openEdit(item)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                        title="Tahrirlash"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </PermissionGate>
                    <PermissionGate permission={deletePermission}>
                      <button
                        onClick={() => setDeleteId(item.id)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        title="O'chirish"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </PermissionGate>
                  </div>
                </td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={columns.length + 2} className="px-5 py-12 text-center text-gray-400 dark:text-slate-500">
                  {search.trim()
                    ? "Qidiruv bo'yicha topilmadi"
                    : "Ma'lumot yo'q"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>

      <Pagination page={page} pages={totalPages} onPageChange={setPage} />

      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500">
        {search.trim() && searchKeys && searchKeys.length > 0
          ? `Topildi: ${filteredItems.length} / ${items.length}`
          : `Jami: ${items.length}`}
      </p>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-[2px] flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-fade-in">
          <div className="md3-dialog w-full sm:max-w-md max-h-[92vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl p-5 sm:p-6 safe-pb">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editingItem ? "Tahrirlash" : "Yangi qo'shish"}
            </h3>

            {formError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">
                {formError}
              </div>
            )}

            <div className="space-y-4">
              {formFields.map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {f.label} {f.required && "*"}
                  </label>
                  {f.type === "select" ? (
                    <Md3Select
                      value={form[f.key] != null ? String(form[f.key]) : ""}
                      onChange={(v) => setForm({ ...form, [f.key]: v })}
                      placeholder="Tanlang..."
                      options={(f.options ?? []).map((o) => ({
                        value: String(o.value),
                        label: o.label,
                      }))}
                    />
                  ) : (
                    <input
                      type={f.type}
                      value={form[f.key] ?? ""}
                      onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                      className="input-field w-full"
                      placeholder={f.placeholder || f.label}
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? "Saqlanmoqda..." : editingItem ? "Saqlash" : "Yaratish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteId !== null && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-[2px] flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-fade-in">
          <div className="md3-dialog w-full sm:max-w-sm rounded-t-3xl sm:rounded-3xl p-6 text-center safe-pb">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">O'chirishni tasdiqlang</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">Bu amalni qaytarib bo'lmaydi</p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button
                onClick={() => handleDelete(deleteId)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                O'chirish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
