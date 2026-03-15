import { useCallback, useState } from "react";
import type { EmbeddingResponse } from "../interfaces";
import { extractEmbeddingApi, fileToBase64 } from "../api";
import { extractErrorMessage } from "../utils/errorMessage";

type InputMode = "file" | "base64";

export default function EmbeddingPage() {
  const [mode, setMode] = useState<InputMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [base64Input, setBase64Input] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<EmbeddingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [b64Copied, setB64Copied] = useState(false);
  const [imgBase64, setImgBase64] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = useCallback((selected: File) => {
    setFile(selected);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(selected);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) handleFileSelect(selected);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type.startsWith("image/")) handleFileSelect(dropped);
  }, [handleFileSelect]);

  const handleBase64Change = (value: string) => {
    setBase64Input(value);
    setResult(null);
    setError(null);
    if (value.trim()) {
      const src = value.trim().startsWith("data:") ? value.trim() : `data:image/jpeg;base64,${value.trim()}`;
      setPreview(src);
    } else {
      setPreview(null);
    }
  };

  const canSubmit = mode === "file" ? !!file : base64Input.trim().length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setImgBase64(null);
    try {
      let b64: string;
      if (mode === "file") {
        b64 = await fileToBase64(file!);
      } else {
        b64 = base64Input.trim();
      }
      setImgBase64(b64);
      const res = await extractEmbeddingApi({ img_b64: b64 });
      setResult(res);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode: InputMode) => {
    setMode(newMode);
    setFile(null);
    setBase64Input("");
    setPreview(null);
    setResult(null);
    setError(null);
  };

  const copyText = (text: string, setter: (v: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setter(true);
    setTimeout(() => setter(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Compact Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center shadow-sm">
          <svg className="w-4.5 h-4.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900 dark:text-white">Yuz Embedding</h1>
          <p className="text-xs text-gray-400 dark:text-slate-500">Rasmdan embedding vektorini olish</p>
        </div>
      </div>

      {/* Input Card — compact */}
      <form onSubmit={handleSubmit} className="rounded-2xl bg-white dark:bg-slate-800 ring-1 ring-gray-200/70 dark:ring-slate-700/60 shadow-sm overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-gray-100 dark:border-slate-700/50">
          {([
            { key: "file" as InputMode, label: "Rasm yuklash", icon: "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" },
            { key: "base64" as InputMode, label: "Base64 string", icon: "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" },
          ]).map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => switchMode(tab.key)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold tracking-wide uppercase transition-all duration-200 border-b-2 ${
                mode === tab.key
                  ? "border-primary-500 text-primary-600 dark:text-primary-400"
                  : "border-transparent text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
              </svg>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-5 space-y-4">
          {/* File Drop Zone — compact */}
          {mode === "file" && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`relative flex items-center gap-4 rounded-xl border-2 border-dashed p-4 transition-all duration-200 cursor-pointer ${
                dragOver
                  ? "border-primary-400 bg-primary-50/40 dark:bg-primary-900/10"
                  : file
                  ? "border-green-300 dark:border-green-800 bg-green-50/30 dark:bg-green-900/10"
                  : "border-gray-200 dark:border-slate-600 hover:border-primary-300 dark:hover:border-primary-700 bg-gray-50/40 dark:bg-slate-900/20"
              }`}
            >
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                file ? "bg-green-100 dark:bg-green-900/30" : "bg-gray-100 dark:bg-slate-700"
              }`}>
                {file ? (
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                )}
              </div>
              <div className="min-w-0">
                {file ? (
                  <>
                    <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{file.name}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-gray-600 dark:text-slate-300">Rasmni tashlang yoki tanlang</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">JPG, PNG, WebP</p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Base64 Input */}
          {mode === "base64" && (
            <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-slate-600 bg-gray-50/40 dark:bg-slate-900/20 p-4 transition-all duration-200 focus-within:border-primary-400 dark:focus-within:border-primary-500 focus-within:bg-primary-50/20 dark:focus-within:bg-primary-900/10">
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
                  <svg className="w-4 h-4 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-slate-300">Base64 string kiriting</p>
                  <p className="text-[11px] text-gray-400 dark:text-slate-500">data:image prefiksi bilan yoki sof base64</p>
                </div>
                {base64Input.trim() && (
                  <span className="ml-auto text-[10px] font-medium text-primary-500 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-0.5 rounded-full">
                    {(base64Input.trim().length / 1024).toFixed(1)} KB
                  </span>
                )}
              </div>
              <textarea
                value={base64Input}
                onChange={(e) => handleBase64Change(e.target.value)}
                placeholder="/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQ..."
                rows={4}
                className="w-full rounded-lg border-0 bg-white dark:bg-slate-800 px-3.5 py-3 text-xs text-gray-900 dark:text-slate-200 placeholder-gray-300 dark:placeholder-slate-600 focus:ring-2 focus:ring-primary-500/20 outline-none resize-y font-mono shadow-inner transition-all"
              />
            </div>
          )}

          {/* Preview */}
          {preview && (
            <div className="flex justify-center py-2">
              <img
                src={preview}
                alt="Preview"
                className="max-h-52 rounded-2xl ring-1 ring-gray-200 dark:ring-slate-600 shadow-md object-contain"
                onError={() => mode === "base64" && setPreview(null)}
              />
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="w-full py-3 px-5 rounded-xl text-sm font-semibold text-white transition-all duration-200
              bg-primary-600 hover:bg-primary-500 active:scale-[0.98]
              disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
              shadow-sm hover:shadow-md hover:shadow-primary-500/20"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Aniqlanmoqda...
              </span>
            ) : "Embedding olish"}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl bg-red-50 dark:bg-red-900/15 px-4 py-3 ring-1 ring-red-200/80 dark:ring-red-800/40">
          <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="Yuz"
              value={result.detection ? "Aniqlandi" : "Topilmadi"}
              variant={result.detection ? "success" : "error"}
            />
            {result.detection && (
              <StatCard label="Vektor" value={`${result.embedding_size} o'lcham`} variant="primary" />
            )}
            <StatCard label="O'lcham" value={`${result.image_width}x${result.image_height}`} variant="neutral" />
            <StatCard label="Hajm" value={`${(result.file_size_byte / 1024).toFixed(1)} KB`} variant="neutral" />
          </div>

          {/* Errors */}
          {result.error_messages.length > 0 && (
            <div className="rounded-xl bg-red-50 dark:bg-red-900/10 px-4 py-3 ring-1 ring-red-200/60 dark:ring-red-800/30">
              {result.error_messages.map((msg, i) => (
                <p key={i} className="text-xs text-red-600 dark:text-red-400">{msg}</p>
              ))}
            </div>
          )}

          {/* Embedding Vector */}
          {result.detection && result.embedding.length > 0 && (
            <div className="rounded-2xl bg-white dark:bg-slate-800 ring-1 ring-gray-200/70 dark:ring-slate-700/60 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-slate-700/40">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                  </div>
                  <span className="text-sm font-semibold text-gray-800 dark:text-slate-200">Embedding vektor</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">({result.embedding_size}d float32)</span>
                </div>
                <CopyBtn active={copied} onClick={() => copyText(JSON.stringify(result.embedding), setCopied)} />
              </div>

              {/* Chart */}
              <div className="px-4 pt-3 pb-2">
                <div className="flex gap-px h-14 items-end bg-gray-50 dark:bg-slate-900/40 rounded-xl p-2 overflow-hidden">
                  {result.embedding
                    .filter((_, i) => i % Math.ceil(result.embedding.length / 200) === 0)
                    .map((val, i) => {
                      const n = Math.max(0.03, Math.min(1, (val + 3) / 6));
                      return (
                        <div
                          key={i}
                          className="flex-1 min-w-[1.5px] rounded-t-sm"
                          style={{
                            height: `${n * 100}%`,
                            backgroundColor: `hsl(${n > 0.5 ? 160 + (n - 0.5) * 140 : n * 300}, 65%, 50%)`,
                            opacity: 0.8,
                          }}
                        />
                      );
                    })}
                </div>
              </div>

              {/* Values */}
              <div className="px-4 pb-4">
                <div className="max-h-44 overflow-y-auto bg-gray-50 dark:bg-slate-900/40 rounded-xl p-3 font-mono text-[11px] leading-6 ring-1 ring-gray-100 dark:ring-slate-700/40">
                  <span className="text-gray-300 dark:text-slate-600">[</span>
                  {result.embedding.map((v, i) => (
                    <span key={i}>
                      <span className={v >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-500 dark:text-rose-400"}>
                        {v.toFixed(6)}
                      </span>
                      {i < result.embedding.length - 1 && <span className="text-gray-300 dark:text-slate-600">, </span>}
                    </span>
                  ))}
                  <span className="text-gray-300 dark:text-slate-600">]</span>
                </div>
              </div>
            </div>
          )}

          {/* Base64 — faqat rasm yuklanganda */}
          {imgBase64 && mode === "file" && (
            <div className="rounded-2xl bg-white dark:bg-slate-800 ring-1 ring-gray-200/70 dark:ring-slate-700/60 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-slate-700/40">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                  </div>
                  <span className="text-sm font-semibold text-gray-800 dark:text-slate-200">Rasm Base64</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">({(imgBase64.length / 1024).toFixed(1)} KB)</span>
                </div>
                <CopyBtn active={b64Copied} onClick={() => copyText(imgBase64, setB64Copied)} />
              </div>
              <div className="p-4">
                <div className="max-h-32 overflow-y-auto bg-gray-50 dark:bg-slate-900/40 rounded-xl p-3 font-mono text-[11px] text-gray-500 dark:text-slate-400 break-all leading-5 ring-1 ring-gray-100 dark:ring-slate-700/40">
                  {imgBase64}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* Stat Card */
function StatCard({ label, value, variant }: {
  label: string;
  value: string;
  variant: "success" | "error" | "primary" | "neutral";
}) {
  const styles = {
    success: "bg-green-50 dark:bg-green-900/15 ring-green-200/60 dark:ring-green-800/30",
    error: "bg-red-50 dark:bg-red-900/15 ring-red-200/60 dark:ring-red-800/30",
    primary: "bg-primary-50 dark:bg-primary-900/15 ring-primary-200/60 dark:ring-primary-800/30",
    neutral: "bg-gray-50 dark:bg-slate-700/30 ring-gray-200/60 dark:ring-slate-600/30",
  };
  const valueStyles = {
    success: "text-green-700 dark:text-green-400",
    error: "text-red-600 dark:text-red-400",
    primary: "text-primary-700 dark:text-primary-400",
    neutral: "text-gray-800 dark:text-slate-200",
  };

  return (
    <div className={`rounded-xl px-4 py-3 ring-1 ${styles[variant]}`}>
      <p className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-slate-500 font-medium mb-0.5">{label}</p>
      <p className={`text-sm font-bold ${valueStyles[variant]}`}>{value}</p>
    </div>
  );
}

/* Copy Button — compact */
function CopyBtn({ active, onClick }: { active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
        active
          ? "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400"
          : "text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-300"
      }`}
    >
      {active ? (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
      {active ? "OK" : "Nusxa"}
    </button>
  );
}
