import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { PaginatedFaceLogs } from "../interfaces";
import { getFaceLogsApi } from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import AuthImage from "../components/AuthImage";

export default function FaceLogsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<PaginatedFaceLogs | null>(null);
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
      const result = await getFaceLogsApi(params);
      setData(result);
    } finally { setLoading(false); }
  }, [page, dateFrom, dateTo]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const handleFilter = () => { setPage(1); fetchLogs(); };

  return (
    <div>
      <div className="mb-8">
        <h2 className="section-title">Yuz Solishtirish Loglari</h2>
        <p className="section-subtitle">Barcha yuz solishtirish natijalari</p>
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
          <PageLoader />
        ) : !data || data.items.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">Ma'lumot topilmadi</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">ID</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">PS rasm</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">LV rasm</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Foydalanuvchi</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Vaqt</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Natija</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">Ball</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">PS yuz</th>
                  <th className="px-4 py-3.5 text-center font-medium text-gray-500 dark:text-slate-400">LV yuz</th>
                  <th className="px-4 py-3.5 text-left font-medium text-gray-500 dark:text-slate-400">Vaqt (s)</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr key={log.id} onClick={() => navigate(`/face-logs/${log.id}`)} className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition cursor-pointer">
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">#{log.id}</td>
                    <td className="px-4 py-3 text-center">
                      {log.ps_img ? (
                        <AuthImage src={`/admin/face-logs/${log.id}/image/ps?thumb=true`} alt="PS" className="w-10 h-10 object-cover rounded-lg border border-gray-200 dark:border-slate-600 inline-block" />
                      ) : <span className="text-gray-300 dark:text-slate-600 text-xs">&mdash;</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {log.lv_img ? (
                        <AuthImage src={`/admin/face-logs/${log.id}/image/lv?thumb=true`} alt="LV" className="w-10 h-10 object-cover rounded-lg border border-gray-200 dark:border-slate-600 inline-block" />
                      ) : <span className="text-gray-300 dark:text-slate-600 text-xs">&mdash;</span>}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">{log.username}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{new Date(log.timestamp).toLocaleString("uz-UZ")}</td>
                    <td className="px-4 py-3 text-center">{log.verified ? <span className="badge-success">Mos</span> : <span className="badge-error">Mos emas</span>}</td>
                    <td className="px-4 py-3 text-center font-mono text-xs text-gray-700 dark:text-slate-300">{Math.round(log.score * 100)}%</td>
                    <td className="px-4 py-3 text-center"><span className={`inline-block w-2.5 h-2.5 rounded-full ${log.ps_detection ? "bg-emerald-500" : "bg-red-400"}`} /></td>
                    <td className="px-4 py-3 text-center"><span className={`inline-block w-2.5 h-2.5 rounded-full ${log.lv_detection ? "bg-emerald-500" : "bg-red-400"}`} /></td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 text-xs">{log.response_time}s</td>
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
