import { useCallback, useEffect, useState } from "react";
import type { StudentLogListResponse, StudentLogCreate, StudentLogUpdate } from "../interfaces";
import { getStudentLogsApi, createStudentLogApi, updateStudentLogApi, deleteStudentLogApi } from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import { extractErrorMessage } from "../utils/errorMessage";

const emptyForm: StudentLogCreate = {
  student_id: 0,
  score: 0,
  max_score: 0,
  is_check_hand: false,
  ip_address: "",
  mac_address: "",
};

export default function StudentLogsPage() {
  const [data, setData] = useState<StudentLogListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<StudentLogCreate>(emptyForm);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getStudentLogsApi({ page, per_page: 20 });
      setData(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatDate = (val: string | null) => val ? new Date(val).toLocaleString("uz-UZ") : null;

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setFormError("");
    setShowModal(true);
  };

  const openEdit = (log: any) => {
    setEditId(log.id);
    setForm({
      student_id: log.student_id,
      first_captured: log.first_captured || "",
      last_captured: log.last_captured || "",
      first_enter_time: log.first_enter_time ? log.first_enter_time.slice(0, 16) : "",
      last_enter_time: log.last_enter_time ? log.last_enter_time.slice(0, 16) : "",
      score: log.score,
      max_score: log.max_score,
      is_check_hand: log.is_check_hand,
      ip_address: log.ip_address || "",
      mac_address: log.mac_address || "",
    });
    setFormError("");
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.student_id) {
      setFormError("Student ID majburiy");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      if (editId) {
        await updateStudentLogApi(editId, form as StudentLogUpdate);
      } else {
        await createStudentLogApi(form);
      }
      setShowModal(false);
      await fetchData();
    } catch (err: any) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Haqiqatan o'chirmoqchimisiz?")) return;
    try {
      await deleteStudentLogApi(id);
      await fetchData();
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  const setField = (key: string, value: any) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Student kirish loglari</h2>
          <p className="section-subtitle">Studentlarning kirish va tekshiruv loglari</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Yangi log
        </button>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-auto underline text-xs">Yopish</button>
        </div>
      )}

      {data && <div className="mb-5 text-sm text-gray-500 dark:text-slate-400">Jami: {data.total} ta</div>}

      <div className="glass-card overflow-hidden">
        {loading ? <PageLoader /> : !data || data.items.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">Ma'lumot topilmadi</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">ID</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Student</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Birinchi kirish</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Oxirgi kirish</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Ball</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Max ball</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">IP</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">MAC</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Qo'l</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition">
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">#{log.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">{log.student_full_name || `#${log.student_id}`}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 text-xs">{formatDate(log.first_enter_time) || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 text-xs">{formatDate(log.last_enter_time) || "—"}</td>
                    <td className="px-4 py-3 text-center font-medium text-gray-800 dark:text-slate-200">{log.score}</td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-400">{log.max_score}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 font-mono text-xs">{log.ip_address || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 font-mono text-xs">{log.mac_address || "—"}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${log.is_check_hand ? "bg-emerald-500" : "bg-gray-300 dark:bg-slate-600"}`} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button onClick={() => openEdit(log)} className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300" title="Tahrirlash">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                        </button>
                        <button onClick={() => handleDelete(log.id)} className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300" title="O'chirish">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editId ? "Logni tahrirlash" : "Yangi log"}
            </h3>
            {formError && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">{formError}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Student ID *</label>
                <input type="number" value={form.student_id} onChange={(e) => setField("student_id", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Ball</label>
                <input type="number" value={form.score ?? 0} onChange={(e) => setField("score", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Max ball</label>
                <input type="number" value={form.max_score ?? 0} onChange={(e) => setField("max_score", Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">IP manzil</label>
                <input type="text" value={form.ip_address || ""} onChange={(e) => setField("ip_address", e.target.value || null)} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">MAC manzil</label>
                <input type="text" value={form.mac_address || ""} onChange={(e) => setField("mac_address", e.target.value || null)} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Birinchi kirish</label>
                <input type="datetime-local" value={form.first_enter_time || ""} onChange={(e) => setField("first_enter_time", e.target.value || null)} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">Oxirgi kirish</label>
                <input type="datetime-local" value={form.last_enter_time || ""} onChange={(e) => setField("last_enter_time", e.target.value || null)} className="input-field w-full" />
              </div>
              <div className="flex items-center gap-2 col-span-2">
                <input type="checkbox" id="is_check_hand" checked={form.is_check_hand ?? false} onChange={(e) => setField("is_check_hand", e.target.checked)} className="rounded" />
                <label htmlFor="is_check_hand" className="text-sm text-gray-700 dark:text-slate-300">Qo'l tekshiruvi</label>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors">Bekor qilish</button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">{saving ? "Saqlanmoqda..." : "Saqlash"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
