import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { VerificationLogResponse } from "../interfaces";
import { getLogByIdApi } from "../api";
import AuthImage from "../components/AuthImage";
import PageLoader from "../components/PageLoader";

export default function LogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [log, setLog] = useState<VerificationLogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getLogByIdApi(Number(id))
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

  if (loading) return <PageLoader />;

  if (error || !log) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-10 text-center">
          <p className="text-red-600 dark:text-red-400 font-medium mb-4">{error || "Log topilmadi"}</p>
          <Link to="/logs" className="text-primary-600 dark:text-primary-400 hover:underline text-sm">Loglarga qaytish</Link>
        </div>
      </div>
    );
  }

  let bgColorRgb: number[] | null = null;
  if (log.back_color && log.back_color !== "None") {
    try { bgColorRgb = JSON.parse(log.back_color.replace(/'/g, '"')); } catch { /* ignore */ }
  }

  const errorLines = log.error_message ? log.error_message.split("\n").filter(Boolean) : [];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/logs" className="flex items-center gap-1 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          <span className="text-sm">Orqaga</span>
        </Link>
        <h2 className="section-title">Tekshiruv #{log.id}</h2>
        {log.success ? <span className="badge-success">Muvaffaqiyatli</span> : <span className="badge-error">Rad etilgan</span>}
      </div>

      {/* Main content */}
      <div className="glass-card overflow-hidden">
        <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-100 dark:divide-slate-700">
          {/* Rasm */}
          <div className="p-6 flex items-center justify-center bg-gray-50 dark:bg-slate-800/50">
            {log.image_path ? (
              <AuthImage src={`/admin/logs/${log.id}/image`} alt={`#${log.id}`} className="max-w-full max-h-64 rounded-xl border border-gray-200 dark:border-slate-600 shadow-sm object-contain" />
            ) : (
              <div className="w-full h-48 flex items-center justify-center text-gray-300 dark:text-slate-600">
                <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
              </div>
            )}
          </div>

          {/* Left info */}
          <div className="p-6 space-y-5">
            <InfoRow label="Foydalanuvchi" value={log.username} />
            <InfoRow label="Foydalanuvchi ID" value={`#${log.user_id}`} />
            <InfoRow label="Sana va vaqt" value={formatDate(log.timestamp)} />
            <InfoRow label="Kiritilgan yosh" value={`${log.input_age} yosh`} />
          </div>

          {/* Right info */}
          <div className="p-6 space-y-5">
            <div>
              <p className="label-text mb-1">Yuz aniqlash</p>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${log.detection ? "bg-emerald-500" : "bg-red-400"}`} />
                <span className={`text-sm font-medium ${log.detection ? "text-emerald-700 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>{log.detection ? "Aniqlandi" : "Topilmadi"}</span>
              </div>
            </div>
            <InfoRow label="Rasm o'lchami" value={`${log.image_width} x ${log.image_height} px`} mono />
            <InfoRow label="Fayl hajmi" value={formatBytes(log.file_size_bytes)} />
            <div>
              <p className="label-text mb-1">Orqa fon rangi</p>
              {bgColorRgb ? (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg border border-gray-200 dark:border-slate-600 shadow-sm" style={{ backgroundColor: `rgb(${bgColorRgb.join(",")})` }} />
                  <span className="text-sm font-mono text-gray-700 dark:text-slate-300">RGB({bgColorRgb.join(", ")})</span>
                </div>
              ) : <span className="text-sm text-gray-400 dark:text-slate-500">Mavjud emas</span>}
            </div>
          </div>
        </div>
      </div>

      {errorLines.length > 0 && (
        <div className="mt-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-3 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>
            Rad etilish sabablari
          </h3>
          <ul className="space-y-2">
            {errorLines.map((msg, i) => (<li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-400"><span className="text-red-400 mt-0.5 flex-shrink-0">&#x2022;</span>{msg}</li>))}
          </ul>
        </div>
      )}

      {log.success && (
        <div className="mt-6 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-2xl p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center text-white text-lg flex-shrink-0">&#x2713;</div>
            <div>
              <p className="font-semibold text-emerald-800 dark:text-emerald-300">Barcha tekshiruvlar muvaffaqiyatli</p>
              <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-0.5">Rasm sertifikat uchun yaroqli deb topilgan</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="label-text mb-1">{label}</p>
      <p className={`text-sm font-medium text-gray-800 dark:text-slate-200 ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
