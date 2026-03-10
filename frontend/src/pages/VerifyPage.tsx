import { useEffect, useRef, useState } from "react";
import type { PhotoVerifyResponse } from "../interfaces";
import { fileToBase64, getTaskStatus, submitVerifyPhoto } from "../api";

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 40;

export default function VerifyPage() {
  const [age, setAge] = useState<number>(25);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<PhotoVerifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);

  useEffect(() => {
    return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current); };
  }, []);

  const stopPolling = () => {
    if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null; }
    pollAttemptsRef.current = 0;
  };

  const startPolling = (taskId: string) => {
    pollAttemptsRef.current = 0;
    pollIntervalRef.current = setInterval(async () => {
      pollAttemptsRef.current += 1;
      if (pollAttemptsRef.current > POLL_MAX_ATTEMPTS) { stopPolling(); setLoading(false); setError("Server javob bermadi"); return; }
      try {
        const s = await getTaskStatus(taskId);
        if (s.status === "SUCCESS" && s.result) { stopPolling(); setResult(s.result); setLoading(false); }
        else if (s.status === "FAILURE") { stopPolling(); setLoading(false); setError(s.error || "Xato"); }
      } catch { stopPolling(); setLoading(false); setError("Tarmoq xatosi"); }
    }, POLL_INTERVAL_MS);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected); setResult(null); setError(null);
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(selected);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Iltimos, rasm tanlang"); return; }
    stopPolling(); setLoading(true); setError(null); setResult(null);
    try {
      const img_b64 = await fileToBase64(file);
      const { task_id } = await submitVerifyPhoto({ age, img_b64 });
      startPolling(task_id);
    } catch (err: unknown) {
      setLoading(false);
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || "Server xatosi");
      } else { setError("Tarmoq xatosi"); }
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h2 className="section-title">Rasm Tekshiruv</h2>
        <p className="section-subtitle">Rasmni yuklang va sertifikat uchun yaroqliligini tekshiring</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card p-7 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Rasm tanlash</label>
          <label className="flex flex-col items-center justify-center w-full h-52 border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-2xl cursor-pointer hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all">
            {preview ? (
              <img src={preview} alt="Preview" className="h-full object-contain rounded-2xl p-2" />
            ) : (
              <div className="flex flex-col items-center py-6">
                <div className="w-14 h-14 rounded-2xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center mb-3">
                  <svg className="w-7 h-7 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500 dark:text-slate-400">Rasmni tashlang yoki <span className="text-primary-600 dark:text-primary-400 font-medium">tanlang</span></p>
                <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">JPG, PNG (max 10MB)</p>
              </div>
            )}
            <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Yosh</label>
          <input type="number" min={1} max={120} value={age} onChange={(e) => setAge(Number(e.target.value))} className="input-field" placeholder="Yoshingizni kiriting" />
        </div>

        <button type="submit" disabled={loading || !file} className="btn-primary w-full py-3.5 text-base">
          {loading ? (<span className="flex items-center justify-center gap-2"><div className="w-5 h-5 spinner" />Tekshirilmoqda...</span>) : "Tekshirish"}
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
          <div className={`flex items-center gap-3 p-4 rounded-xl ${result.success ? "bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800" : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"} ${result.error_messages.length > 0 ? "mb-5" : "mb-6"}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 ${result.success ? "bg-emerald-500 text-white" : "bg-red-500 text-white"}`}>
              {result.success ? "\u2713" : "\u2717"}
            </div>
            <p className={`font-semibold ${result.success ? "text-emerald-800 dark:text-emerald-300" : "text-red-800 dark:text-red-300"}`}>
              {result.success ? "Sertifikat uchun yaroqli" : "Sertifikat uchun yaroqsiz"}
            </p>
          </div>

          {result.error_messages.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6">
              <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">Rad etilish sabablari:</p>
              <ul className="space-y-1.5">
                {result.error_messages.map((msg, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-400"><span className="text-red-400 mt-0.5">&#x2022;</span>{msg}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">Yuz aniqlash</p>
              <p className={`text-lg font-semibold mt-1.5 ${result.detection ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>{result.detection ? "Aniqlandi" : "Topilmadi"}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">Fayl hajmi</p>
              <p className="text-lg font-semibold mt-1.5 text-gray-800 dark:text-slate-200">{formatBytes(result.file_size_byte)}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">O'lcham</p>
              <p className="text-lg font-semibold mt-1.5 text-gray-800 dark:text-slate-200">{result.size.width} x {result.size.height}</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text">Orqa fon rangi</p>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="w-6 h-6 rounded-lg border border-gray-300 dark:border-slate-600" style={{ backgroundColor: `rgb(${result.back_color.join(",")})` }} />
                <p className="text-sm font-mono text-gray-700 dark:text-slate-300">[{result.back_color.join(", ")}]</p>
              </div>
            </div>
            <div className="col-span-2 bg-gray-50 dark:bg-slate-800 rounded-xl p-4">
              <p className="label-text mb-3">Palitra RGB</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400 dark:text-slate-500">Min</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-5 h-5 rounded border border-gray-300 dark:border-slate-600" style={{ backgroundColor: `rgb(${result.palitra_rgb.min_palitra.join(",")})` }} />
                    <span className="text-sm font-mono text-gray-700 dark:text-slate-300">[{result.palitra_rgb.min_palitra.join(", ")}]</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-400 dark:text-slate-500">Max</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-5 h-5 rounded border border-gray-300 dark:border-slate-600" style={{ backgroundColor: `rgb(${result.palitra_rgb.max_palitra.join(",")})` }} />
                    <span className="text-sm font-mono text-gray-700 dark:text-slate-300">[{result.palitra_rgb.max_palitra.join(", ")}]</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
