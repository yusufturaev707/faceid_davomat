import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { PaginatedLogs } from "../interfaces";
import { getLogsApi } from "../api";
import Pagination from "../components/Pagination";
import AuthImage from "../components/AuthImage";

export default function LogsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<PaginatedLogs | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, per_page: 20 };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const result = await getLogsApi(params);
      setData(result);
    } finally { setLoading(false); }
  }, [page, dateFrom, dateTo]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const handleFilter = () => { setPage(1); fetchLogs(); };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div>
      <div className="mb-8">
        <h2 className="section-title">Tekshiruv Loglari</h2>
        <p className="section-subtitle">Barcha rasm tekshiruv natijalari</p>
      </div>

      {/* Filters */}
      <div className="glass-card p-5 mb-5 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">Boshlanish</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input-field !py-2 !text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1.5 font-medium">Tugash</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input-field !py-2 !text-sm" />
        </div>
        <button onClick={handleFilter} className="btn-primary !py-2 text-sm">Filtrlash</button>
        {(dateFrom || dateTo) && (
          <button onClick={() => { setDateFrom(""); setDateTo(""); setPage(1); }} className="btn-secondary !py-2 text-sm">Tozalash</button>
        )}
        {data && <span className="text-sm text-gray-500 dark:text-slate-400 ml-auto">Jami: {data.total} ta</span>}
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32"><div className="w-8 h-8 spinner" /></div>
        ) : !data || data.items.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">Ma'lumot topilmadi</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">ID</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Rasm</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Foydalanuvchi</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Vaqt</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Natija</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Yuz</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">O'lcham</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Hajm</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Yosh</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr key={log.id} onClick={() => navigate(`/logs/${log.id}`)} className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition cursor-pointer">
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">#{log.id}</td>
                    <td className="px-4 py-3 text-center">
                      {log.image_path ? (
                        <AuthImage src={`/admin/logs/${log.id}/image?thumb=true`} alt="Rasm" className="w-10 h-14 object-cover rounded-lg border border-gray-200 dark:border-slate-600 inline-block" />
                      ) : <span className="text-gray-300 dark:text-slate-600 text-xs">&mdash;</span>}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">{log.username}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{new Date(log.timestamp).toLocaleString("uz-UZ")}</td>
                    <td className="px-4 py-3 text-center">{log.success ? <span className="badge-success">OK</span> : <span className="badge-error">Rad</span>}</td>
                    <td className="px-4 py-3 text-center"><span className={`inline-block w-2.5 h-2.5 rounded-full ${log.detection ? "bg-emerald-500" : "bg-red-400"}`} /></td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 font-mono text-xs">{log.image_width}x{log.image_height}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 text-xs">{formatBytes(log.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-400">{log.input_age}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />}
    </div>
  );
}
