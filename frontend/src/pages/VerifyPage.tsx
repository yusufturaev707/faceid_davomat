import { useState } from "react";
import type { PhotoVerifyResponse } from "../interfaces";
import { fileToBase64, verifyPhoto } from "../api";

export default function VerifyPage() {
  const [age, setAge] = useState<number>(25);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<PhotoVerifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(selected);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Iltimos, rasm tanlang");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const img_b64 = await fileToBase64(file);
      const response = await verifyPhoto({ age, img_b64 });
      setResult(response);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || "Server xatosi");
      } else {
        setError("Tarmoq xatosi");
      }
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Rasm Tekshiruv</h2>
        <p className="text-gray-500 text-sm mt-1">Rasmni yuklang va sertifikat uchun yaroqliligini tekshiring</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-6">
        {/* Rasm yuklash */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Rasm tanlash</label>
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
              {preview ? (
                <img src={preview} alt="Preview" className="h-full object-contain rounded-xl" />
              ) : (
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-sm text-gray-500">
                    Rasmni bu yerga tashlang yoki <span className="text-blue-500 font-medium">tanlang</span>
                  </p>
                  <p className="text-xs text-gray-400 mt-1">JPG, PNG (max 10MB)</p>
                </div>
              )}
              <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </label>
          </div>
        </div>

        {/* Yosh */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Yosh</label>
          <input
            type="number"
            min={1}
            max={120}
            value={age}
            onChange={(e) => setAge(Number(e.target.value))}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
            placeholder="Yoshingizni kiriting"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !file}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Tekshirilmoqda...
            </span>
          ) : (
            "Tekshirish"
          )}
        </button>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
        )}
      </form>

      {/* Natija */}
      {result && (
        <div className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div
            className={`flex items-center gap-3 p-4 rounded-xl ${
              result.success ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
            } ${result.error_messages.length > 0 ? "mb-4" : "mb-6"}`}
          >
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 ${
                result.success ? "bg-green-500 text-white" : "bg-red-500 text-white"
              }`}
            >
              {result.success ? "\u2713" : "\u2717"}
            </div>
            <p className={`font-semibold ${result.success ? "text-green-800" : "text-red-800"}`}>
              {result.success ? "Sertifikat uchun yaroqli" : "Sertifikat uchun yaroqsiz"}
            </p>
          </div>

          {result.error_messages.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-sm font-semibold text-red-800 mb-2">Rad etilish sabablari:</p>
              <ul className="space-y-1">
                {result.error_messages.map((msg, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                    <span className="text-red-400 mt-0.5">&#x2022;</span>
                    {msg}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Yuz aniqlash</p>
              <p className={`text-lg font-semibold mt-1 ${result.detection ? "text-green-600" : "text-red-600"}`}>
                {result.detection ? "Aniqlandi" : "Topilmadi"}
              </p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Fayl hajmi</p>
              <p className="text-lg font-semibold mt-1 text-gray-800">{formatBytes(result.file_size_byte)}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">O'lcham</p>
              <p className="text-lg font-semibold mt-1 text-gray-800">{result.size.width} x {result.size.height}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Orqa fon rangi</p>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-6 h-6 rounded border border-gray-300" style={{ backgroundColor: `rgb(${result.back_color.join(",")})` }} />
                <p className="text-sm font-mono text-gray-700">[{result.back_color.join(", ")}]</p>
              </div>
            </div>
            <div className="col-span-2 bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Palitra RGB</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">Min</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-5 h-5 rounded border border-gray-300" style={{ backgroundColor: `rgb(${result.palitra_rgb.min_palitra.join(",")})` }} />
                    <span className="text-sm font-mono">[{result.palitra_rgb.min_palitra.join(", ")}]</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Max</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-5 h-5 rounded border border-gray-300" style={{ backgroundColor: `rgb(${result.palitra_rgb.max_palitra.join(",")})` }} />
                    <span className="text-sm font-mono">[{result.palitra_rgb.max_palitra.join(", ")}]</span>
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
