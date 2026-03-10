import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { FaceLogResponse } from "../interfaces";
import { getFaceLogByIdApi } from "../api";
import AuthImage from "../components/AuthImage";

export default function FaceLogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [log, setLog] = useState<FaceLogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getFaceLogByIdApi(Number(id))
      .then(setLog)
      .catch(() => setError("Log topilmadi"))
      .finally(() => setLoading(false));
  }, [id]);

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (ts: string) => new Date(ts).toLocaleString("uz-UZ", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-10 h-10 spinner" /></div>;

  if (error || !log) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-10 text-center">
          <p className="text-red-600 dark:text-red-400 font-medium mb-4">{error || "Log topilmadi"}</p>
          <Link to="/face-logs" className="text-primary-600 dark:text-primary-400 hover:underline text-sm">Loglarga qaytish</Link>
        </div>
      </div>
    );
  }

  const scorePercent = Math.round(log.score * 100);
  const errorLines = log.error_message ? log.error_message.split("\n").filter(Boolean) : [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/face-logs" className="flex items-center gap-1 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          <span className="text-sm">Orqaga</span>
        </Link>
        <h2 className="section-title">Solishtirish #{log.id}</h2>
        {log.verified ? <span className="badge-success">Mos keldi</span> : <span className="badge-error">Mos kelmadi</span>}
      </div>

      {/* Score */}
      <div className="glass-card p-6 mb-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">O'xshashlik balli</span>
          <span className="text-2xl font-bold text-gray-900 dark:text-white">{scorePercent}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-4">
          <div className={`h-4 rounded-full transition-all ${log.verified ? "bg-emerald-500" : "bg-red-500"}`} style={{ width: `${Math.min(scorePercent, 100)}%` }} />
        </div>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-2">Chegara: {Math.round(log.thresh_score * 100)}% | Javob vaqti: {log.response_time}s</p>
      </div>

      {/* Images */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {[
          { label: "Pasport rasmi (PS)", img: log.ps_img, type: "ps" as const, w: log.ps_width, h: log.ps_height, size: log.ps_file_size, det: log.ps_detection },
          { label: "Jonli rasm (LV)", img: log.lv_img, type: "lv" as const, w: log.lv_width, h: log.lv_height, size: log.lv_file_size, det: log.lv_detection },
        ].map((item) => (
          <div key={item.type} className="glass-card overflow-hidden">
            <div className="px-5 py-3 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-100 dark:border-slate-700">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">{item.label}</h3>
            </div>
            <div className="p-5 flex items-center justify-center min-h-[200px]">
              {item.img ? (
                <AuthImage src={`/admin/face-logs/${log.id}/image/${item.type}`} alt={item.type.toUpperCase()} className="max-w-full max-h-64 rounded-xl object-contain" />
              ) : (
                <div className="text-gray-300 dark:text-slate-600">
                  <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
              )}
            </div>
            <div className="px-5 py-3 bg-gray-50 dark:bg-slate-800/50 border-t border-gray-100 dark:border-slate-700 grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-slate-400">
              <div><span className="text-gray-400 dark:text-slate-500">O'lcham:</span> {item.w}x{item.h}</div>
              <div><span className="text-gray-400 dark:text-slate-500">Hajm:</span> {formatBytes(item.size)}</div>
              <div className="col-span-2">
                <span className="text-gray-400 dark:text-slate-500">Yuz:</span>{" "}
                <span className={item.det ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}>{item.det ? "Aniqlandi" : "Topilmadi"}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="glass-card p-6 mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div><p className="label-text mb-1">Foydalanuvchi</p><p className="text-sm font-medium text-gray-800 dark:text-slate-200">{log.username}</p></div>
          <div><p className="label-text mb-1">Sana va vaqt</p><p className="text-sm font-medium text-gray-800 dark:text-slate-200">{formatDate(log.timestamp)}</p></div>
          <div><p className="label-text mb-1">Yuz aniqlash</p><p className={`text-sm font-medium ${log.detection ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>{log.detection ? "Ikkala yuzda" : "Kamida biri topilmadi"}</p></div>
          <div><p className="label-text mb-1">Javob vaqti</p><p className="text-sm font-medium text-gray-800 dark:text-slate-200">{log.response_time}s</p></div>
        </div>
      </div>

      {errorLines.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-3 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>
            Xatoliklar
          </h3>
          <ul className="space-y-2">
            {errorLines.map((msg, i) => (<li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-400"><span className="text-red-400 mt-0.5 flex-shrink-0">&#x2022;</span>{msg}</li>))}
          </ul>
        </div>
      )}
    </div>
  );
}
