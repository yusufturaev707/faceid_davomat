import { useEffect, useRef, useState } from "react";
import type { TwoFaceVerifyResponse } from "../interfaces";
import { fileToBase64, getTwoFaceTaskStatus, submitVerifyTwoFace } from "../api";
import { extractErrorMessage } from "../utils/errorMessage";

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 40;

export default function VerifyTwoFacePage() {
  const [psFile, setPsFile] = useState<File | null>(null);
  const [lvFile, setLvFile] = useState<File | null>(null);
  const [psPreview, setPsPreview] = useState<string | null>(null);
  const [lvPreview, setLvPreview] = useState<string | null>(null);
  const [result, setResult] = useState<TwoFaceVerifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);

  useEffect(() => { return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current); }; }, []);

  const stopPolling = () => { if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null; } pollAttemptsRef.current = 0; };

  const startPolling = (taskId: string) => {
    pollAttemptsRef.current = 0;
    pollIntervalRef.current = setInterval(async () => {
      pollAttemptsRef.current += 1;
      if (pollAttemptsRef.current > POLL_MAX_ATTEMPTS) { stopPolling(); setLoading(false); setError("So'rov vaqti tugadi. Server javob bermadi. Keyinroq urinib ko'ring"); return; }
      try {
        const s = await getTwoFaceTaskStatus(taskId);
        if (s.status === "SUCCESS" && s.result) { stopPolling(); setResult(s.result); setLoading(false); }
        else if (s.status === "FAILURE") { stopPolling(); setLoading(false); setError(s.error || "Solishtirish muvaffaqiyatsiz yakunlandi"); }
      } catch (err) { stopPolling(); setLoading(false); setError(extractErrorMessage(err)); }
    }, POLL_INTERVAL_MS);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: "ps" | "lv") => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setResult(null); setError(null);
    const reader = new FileReader();
    if (type === "ps") { setPsFile(selected); reader.onload = () => setPsPreview(reader.result as string); }
    else { setLvFile(selected); reader.onload = () => setLvPreview(reader.result as string); }
    reader.readAsDataURL(selected);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!psFile || !lvFile) { setError("Iltimos, ikkala rasmni tanlang"); return; }
    stopPolling(); setLoading(true); setError(null); setResult(null);
    try {
      const ps_img = await fileToBase64(psFile);
      const lv_img = await fileToBase64(lvFile);
      const { task_id } = await submitVerifyTwoFace({ ps_img, lv_img });
      startPolling(task_id);
    } catch (err: unknown) {
      setLoading(false);
      setError(extractErrorMessage(err));
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const scorePercent = result ? Math.round(result.score * 100) : 0;

  const UploadBox = ({ label, preview: prev, type }: { label: string; preview: string | null; type: "ps" | "lv" }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">{label}</label>
      <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-2xl cursor-pointer hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all">
        {prev ? (
          <img src={prev} alt={label} className="h-full object-contain rounded-2xl p-2" />
        ) : (
          <div className="flex flex-col items-center py-4">
            <div className="w-12 h-12 rounded-xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center mb-2">
              <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
          </div>
        )}
        <input type="file" accept="image/*" onChange={(e) => handleFileChange(e, type)} className="hidden" />
      </label>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h2 className="section-title">Yuzlarni Solishtirish</h2>
        <p className="section-subtitle">Ikki rasmdagi yuzlarni o'xshashlikka tekshiring</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-7 space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <UploadBox label="Pasport rasmi" preview={psPreview} type="ps" />
          <UploadBox label="Jonli rasm" preview={lvPreview} type="lv" />
        </div>

        <button type="submit" disabled={loading || !psFile || !lvFile} className="btn-primary w-full py-3.5 text-base">
          {loading ? (<span className="flex items-center justify-center gap-2"><div className="w-5 h-5 spinner" />Solishtirilmoqda...</span>) : "Solishtirish"}
        </button>

        {error && (
          <div className="flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {error}
          </div>
        )}
      </form>

      {result && (
        <div className="mt-6 glass-card p-7">
          <div className={`flex items-center gap-3 p-4 rounded-xl mb-6 ${result.verified ? "bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800" : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 ${result.verified ? "bg-emerald-500 text-white" : "bg-red-500 text-white"}`}>
              {result.verified ? "\u2713" : "\u2717"}
            </div>
            <p className={`font-semibold ${result.verified ? "text-emerald-800 dark:text-emerald-300" : "text-red-800 dark:text-red-300"}`}>{result.message}</p>
          </div>

          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-slate-300">O'xshashlik balli</span>
              <span className="text-sm font-bold text-gray-900 dark:text-white">{scorePercent}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
              <div className={`h-3 rounded-full transition-all ${result.verified ? "bg-emerald-500" : "bg-red-500"}`} style={{ width: `${Math.min(scorePercent, 100)}%` }} />
            </div>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Chegara: {Math.round(result.thresh_score * 100)}%</p>
          </div>

          {result.error_messages.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6">
              <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">Xatoliklar:</p>
              <ul className="space-y-1.5">
                {result.error_messages.map((msg, i) => (<li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-400"><span className="text-red-400 mt-0.5">&#x2022;</span>{msg}</li>))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">PS yuz</p>
              <p className={`text-lg font-semibold mt-1.5 ${result.ps_detection ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>{result.ps_detection ? "Aniqlandi" : "Topilmadi"}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">LV yuz</p>
              <p className={`text-lg font-semibold mt-1.5 ${result.lv_detection ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>{result.lv_detection ? "Aniqlandi" : "Topilmadi"}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">PS o'lcham</p>
              <p className="text-lg font-semibold mt-1.5 text-gray-800 dark:text-slate-200">{result.ps_width} x {result.ps_height}</p>
              <p className="text-xs text-gray-400 dark:text-slate-500">{formatBytes(result.ps_file_size)}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">LV o'lcham</p>
              <p className="text-lg font-semibold mt-1.5 text-gray-800 dark:text-slate-200">{result.lv_width} x {result.lv_height}</p>
              <p className="text-xs text-gray-400 dark:text-slate-500">{formatBytes(result.lv_file_size)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
