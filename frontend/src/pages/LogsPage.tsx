import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { PaginatedLogs } from "../interfaces";
import { getLogsApi } from "../api";
import Pagination from "../components/Pagination";

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
    } finally {
      setLoading(false);
    }
  }, [page, dateFrom, dateTo]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleFilter = () => {
    setPage(1);
    fetchLogs();
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Tekshiruv Loglari</h2>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Boshlanish sanasi</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tugash sanasi</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <button
          onClick={handleFilter}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition"
        >
          Filtrlash
        </button>
        {(dateFrom || dateTo) && (
          <button
            onClick={() => {
              setDateFrom("");
              setDateTo("");
              setPage(1);
            }}
            className="px-4 py-2 text-gray-600 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition"
          >
            Tozalash
          </button>
        )}
        {data && (
          <span className="text-sm text-gray-500 ml-auto">
            Jami: {data.total} ta yozuv
          </span>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin h-6 w-6 border-4 border-blue-500 border-t-transparent rounded-full" />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Ma'lumot topilmadi</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left font-medium text-gray-600">ID</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Foydalanuvchi</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Vaqt</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Natija</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Yuz</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">O'lcham</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Hajm</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Yosh</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => navigate(`/logs/${log.id}`)}
                    className="border-b border-gray-100 hover:bg-blue-50 transition cursor-pointer"
                  >
                    <td className="px-4 py-3 text-gray-500">#{log.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{log.username}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(log.timestamp).toLocaleString("uz-UZ")}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          log.success
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {log.success ? "OK" : "Rad"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          log.detection ? "bg-green-500" : "bg-red-400"
                        }`}
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                      {log.image_width}x{log.image_height}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{formatBytes(log.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-center text-gray-600">{log.input_age}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && (
        <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />
      )}
    </div>
  );
}
