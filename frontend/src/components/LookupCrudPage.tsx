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
  /** Ixtiyoriy: ro'yxatni ko'rsatishdan oldin tartiblash (masalan, Binolar —
   *  viloyat raqami, so'ng bino raqami bo'yicha). Filtr va paginatsiyadan oldin
   *  qo'llanadi. */
  sortItems?: (items: T[]) => T[];
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
  sortItems,
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

  const hasStatus = items.some((i) => "is_active" in i);

  useEffect(() => {
    load();
  }, []);

  // Modal ochiq bo'lganda orqa fon scroll'ini bloklaymiz — scrollbar
  // yo'qolib sahifa "sakramasligi" uchun kengligini padding bilan to'ldiramiz.
  useEffect(() => {
    const anyOpen = showModal || deleteId !== null;
    if (!anyOpen) return;
    const scrollbarW = window.innerWidth - document.documentElement.clientWidth;
    const prevOverflow = document.body.style.overflow;
    const prevPad = document.body.style.paddingRight;
    document.body.style.overflow = "hidden";
    if (scrollbarW > 0) document.body.style.paddingRight = `${scrollbarW}px`;
    return () => {
      document.body.style.overflow = prevOverflow;
      document.body.style.paddingRight = prevPad;
    };
  }, [showModal, deleteId]);

  // Tartiblangan ro'yxat — `sortItems` berilsa qo'llanadi (filtr/paginatsiyadan oldin)
  const sortedItems = useMemo(
    () => (sortItems ? sortItems(items) : items),
    [items, sortItems],
  );

  const filteredItems = useMemo(() => {
    if (!searchKeys || searchKeys.length === 0) return sortedItems;
    const q = search.trim().toLowerCase();
    if (!q) return sortedItems;
    return sortedItems.filter((it) =>
      searchKeys.some((k) => {
        const val = (it as any)[k];
        return val != null && String(val).toLowerCase().includes(q);
      }),
    );
  }, [sortedItems, search, searchKeys]);

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
      <div>
        <div className="page-header">
          <div className="min-w-0">
            <h2 className="section-title">{title}</h2>
            <p className="section-subtitle">{subtitle}</p>
          </div>
        </div>
        <TableSkeleton cols={columns.length + (hasStatus ? 2 : 1)} />
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
        <div className="mb-4 p-3.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-2xl text-sm flex items-start justify-between gap-3 ring-1 ring-red-200/60 dark:ring-red-800/40">
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M5 13a7 7 0 1114 0v6a2 2 0 01-2 2H7a2 2 0 01-2-2v-6z" />
            </svg>
            {error}
          </span>
          <button onClick={() => setError("")} className="underline shrink-0">Yopish</button>
        </div>
      )}

      {/* Search */}
      {searchKeys && searchKeys.length > 0 && (
        <div className="mb-4">
          <div className="relative max-w-md">
            <svg
              className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
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
              className="w-full h-11 pl-10 pr-10 rounded-full border border-gray-300 dark:border-slate-600 bg-surface dark:bg-slate-800 text-sm text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:ring-4 focus:ring-primary-500/15 focus:border-primary-500 outline-none transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-slate-300 dark:hover:bg-slate-700/60 transition-colors"
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
        <table className="w-full min-w-[600px] border-collapse">
          <thead>
            <tr className="bg-gray-50/70 dark:bg-slate-800/40 border-b border-gray-200/70 dark:border-slate-700/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-[0.08em] whitespace-nowrap"
                >
                  {col.label}
                </th>
              ))}
              {hasStatus && (
                <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-[0.08em] whitespace-nowrap">
                  Holat
                </th>
              )}
              <th className="text-right px-5 py-3.5 text-[11px] font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-[0.08em] whitespace-nowrap">
                Amallar
              </th>
            </tr>
          </thead>
          <tbody>
            {pagedItems.map((item, idx) => (
              <tr
                key={item.id}
                className={`group border-b border-gray-100/70 dark:border-slate-700/30 last:border-0 transition-colors duration-150 ${
                  idx % 2 === 1
                    ? "bg-gray-50/40 dark:bg-slate-800/20"
                    : ""
                } hover:bg-primary-50/50 dark:hover:bg-primary-900/15`}
              >
                {columns.map((col, ci) => (
                  <td
                    key={col.key}
                    className={`px-5 py-4 text-sm leading-relaxed ${
                      ci === 0 ? "" : "text-gray-600 dark:text-slate-300"
                    }`}
                  >
                    {col.render
                      ? col.render((item as any)[col.key], item)
                      : ci === 0
                        ? (
                            <span className="inline-flex items-center justify-center min-w-[2.25rem] px-2 py-0.5 rounded-md bg-gray-100 dark:bg-slate-700/50 text-gray-500 dark:text-slate-400 font-mono tabular-nums text-[11px] font-medium ring-1 ring-inset ring-gray-200/50 dark:ring-slate-600/40 group-hover:bg-primary-100/60 group-hover:text-primary-700 dark:group-hover:bg-primary-900/30 dark:group-hover:text-primary-300 transition-colors">
                              {(item as any)[col.key]}
                            </span>
                          )
                        : (col.key === "name" ? (
                            <span className="font-semibold text-gray-800 dark:text-slate-100">
                              {String((item as any)[col.key] ?? "—")}
                            </span>
                          ) : (
                            String((item as any)[col.key] ?? "—")
                          ))}
                  </td>
                ))}
                {hasStatus && (
                  <td className="px-5 py-4">
                    <PermissionGate
                      permission={updatePermission}
                      fallback={<StatusPill active={!!(item as any).is_active} />}
                    >
                      <button
                        onClick={() => toggleActive(item)}
                        title="Holatni o'zgartirish"
                        className="transition-transform active:scale-95"
                      >
                        <StatusPill active={!!(item as any).is_active} interactive />
                      </button>
                    </PermissionGate>
                  </td>
                )}
                <td className="px-5 py-4 text-right">
                  <div className="flex items-center justify-end gap-1.5">
                    <PermissionGate permission={updatePermission}>
                      <button
                        onClick={() => openEdit(item)}
                        className="inline-flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-primary-600 hover:bg-primary-100/70 dark:hover:bg-primary-900/30 transition-colors"
                        title="Tahrirlash"
                      >
                        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </PermissionGate>
                    <PermissionGate permission={deletePermission}>
                      <button
                        onClick={() => setDeleteId(item.id)}
                        className="inline-flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-red-600 hover:bg-red-100/70 dark:hover:bg-red-900/30 transition-colors"
                        title="O'chirish"
                      >
                        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                <td colSpan={columns.length + (hasStatus ? 2 : 1)} className="px-5 py-16 text-center">
                  <div className="flex flex-col items-center gap-3 text-gray-400 dark:text-slate-500">
                    <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
                      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                      </svg>
                    </div>
                    <p className="text-sm font-medium">
                      {search.trim() ? "Qidiruv bo'yicha topilmadi" : "Ma'lumot yo'q"}
                    </p>
                  </div>
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
        <div
          className="fixed inset-0 bg-black/45 dark:bg-black/65 backdrop-blur-[3px] flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-modal-overlay"
          onClick={() => !saving && setShowModal(false)}
        >
          <div
            className="md3-dialog w-full sm:max-w-md max-h-[92vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl safe-pb animate-modal-panel"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-5 sm:px-6 pt-5 pb-4 border-b border-gray-100 dark:border-slate-700/60">
              <div
                className={`w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 ring-1 ${
                  editingItem
                    ? "bg-amber-100 text-amber-600 ring-amber-200/60 dark:bg-amber-900/30 dark:text-amber-400 dark:ring-amber-800/40"
                    : "bg-primary-100 text-primary-600 ring-primary-200/60 dark:bg-primary-900/30 dark:text-primary-400 dark:ring-primary-800/40"
                }`}
              >
                {editingItem ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white leading-tight">
                  {editingItem ? "Tahrirlash" : "Yangi qo'shish"}
                </h3>
                <p className="text-[12px] text-gray-500 dark:text-slate-400 leading-tight mt-0.5 truncate">
                  {title}
                </p>
              </div>
              <button
                onClick={() => !saving && setShowModal(false)}
                className="p-2 -mr-1 rounded-full text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors shrink-0"
                aria-label="Yopish"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="px-5 sm:px-6 py-5">
              {formError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm flex items-center gap-2 ring-1 ring-red-200/60 dark:ring-red-800/40">
                  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M5 13a7 7 0 1114 0v6a2 2 0 01-2 2H7a2 2 0 01-2-2v-6z" />
                  </svg>
                  <span>{formError}</span>
                </div>
              )}

              <div className="space-y-4">
                {formFields.map((f) => (
                  <div key={f.key}>
                    <label className="block text-[13px] font-semibold text-gray-700 dark:text-slate-300 mb-1.5">
                      {f.label}
                      {f.required && <span className="text-red-500 ml-0.5">*</span>}
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
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !saving) handleSave();
                        }}
                        className="input-field w-full"
                        placeholder={f.placeholder || f.label}
                        autoFocus={f === formFields[0]}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2 px-5 sm:px-6 pb-5 pt-1">
              <button
                onClick={() => setShowModal(false)}
                disabled={saving}
                className="px-5 h-11 rounded-full text-sm font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700/60 disabled:opacity-50 transition-colors"
              >
                Bekor qilish
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary min-w-[110px]">
                {saving ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Saqlanmoqda...
                  </>
                ) : editingItem ? (
                  "Saqlash"
                ) : (
                  "Yaratish"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteId !== null && (
        <div
          className="fixed inset-0 bg-black/45 dark:bg-black/65 backdrop-blur-[3px] flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-modal-overlay"
          onClick={() => setDeleteId(null)}
        >
          <div
            className="md3-dialog w-full sm:max-w-sm rounded-t-3xl sm:rounded-3xl p-6 text-center safe-pb animate-modal-panel"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-red-100 dark:bg-red-900/30 ring-1 ring-red-200/60 dark:ring-red-800/40 flex items-center justify-center">
              <svg className="w-7 h-7 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">O'chirishni tasdiqlang</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">
              Bu amalni qaytarib bo'lmaydi. Yozuv butunlay o'chiriladi.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteId(null)}
                className="flex-1 h-11 rounded-full text-sm font-medium text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors"
              >
                Bekor qilish
              </button>
              <button
                onClick={() => handleDelete(deleteId)}
                className="flex-1 h-11 rounded-full text-sm font-semibold text-white bg-red-600 hover:bg-red-700 active:bg-red-800 shadow-sm shadow-red-600/25 transition-colors"
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

/** Faol / Nofaol holat chipi — MD3 tonal pill. */
function StatusPill({ active, interactive = false }: { active: boolean; interactive?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ring-1 transition-colors ${
        active
          ? "bg-emerald-50 text-emerald-700 ring-emerald-200/60 dark:bg-emerald-900/20 dark:text-emerald-400 dark:ring-emerald-800/40"
          : "bg-gray-100 text-gray-500 ring-gray-200/70 dark:bg-slate-700/40 dark:text-slate-400 dark:ring-slate-600/50"
      } ${interactive ? (active ? "hover:bg-emerald-100 dark:hover:bg-emerald-900/30" : "hover:bg-gray-200 dark:hover:bg-slate-700/60") : ""}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-emerald-500" : "bg-gray-400 dark:bg-slate-500"}`} />
      {active ? "Faol" : "Nofaol"}
    </span>
  );
}

/** Yuklanish paytidagi skeleton jadval — layout shift'ni kamaytiradi. */
function TableSkeleton({ cols }: { cols: number }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="bg-gray-50/80 dark:bg-slate-800/60 border-b border-gray-200/70 dark:border-slate-700/60 px-5 py-3.5">
        <div className="h-3 w-24 rounded bg-gray-200 dark:bg-slate-700 animate-pulse" />
      </div>
      <div className="divide-y divide-gray-100/80 dark:divide-slate-700/40">
        {Array.from({ length: 8 }).map((_, r) => (
          <div key={r} className="flex items-center gap-4 px-5 py-4">
            {Array.from({ length: cols }).map((_, c) => (
              <div
                key={c}
                className="h-3.5 rounded bg-gray-200 dark:bg-slate-700 animate-pulse"
                style={{ width: c === 0 ? "2rem" : c === 1 ? "40%" : "20%", animationDelay: `${(r * cols + c) * 25}ms` }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
