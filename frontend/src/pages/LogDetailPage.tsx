import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { VerificationLogResponse } from "../interfaces";
import { getLogByIdApi } from "../api";
import { getAccessToken } from "../tokenStore";

export default function LogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [log, setLog] = useState<VerificationLogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getLogByIdApi(Number(id))
      .then((data) => {
        setLog(data);
        // Agar rasm mavjud bo'lsa, JWT bilan yuklash
        if (data.image_path) {
          const token = getAccessToken();
          fetch(`/api/v1/admin/logs/${data.id}/image`, {
            headers: { Authorization: `Bearer ${token}` },
          })
            .then((res) => (res.ok ? res.blob() : null))
            .then((blob) => {
              if (blob) setImageUrl(URL.createObjectURL(blob));
            })
            .catch(() => {});
        }
      })
      .catch(() => setError("Log topilmadi"))
      .finally(() => setLoading(false));
  }, [id]);

  // Blob URL ni tozalash
  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString("uz-UZ", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !log) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
          <p className="text-red-700 font-medium mb-4">{error || "Log topilmadi"}</p>
          <Link to="/logs" className="text-blue-600 hover:underline text-sm">
            Loglarga qaytish
          </Link>
        </div>
      </div>
    );
  }

  // back_color ni parse qilish: "[R, G, B]" yoki "None"
  let bgColorRgb: number[] | null = null;
  if (log.back_color && log.back_color !== "None") {
    try {
      bgColorRgb = JSON.parse(log.back_color.replace(/'/g, '"'));
    } catch {
      // ignore
    }
  }

  const errorLines = log.error_message ? log.error_message.split("\n").filter(Boolean) : [];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          to="/logs"
          className="flex items-center gap-1 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-sm">Orqaga</span>
        </Link>
        <h2 className="text-2xl font-bold text-gray-800">Tekshiruv #{log.id}</h2>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            log.success
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {log.success ? "Muvaffaqiyatli" : "Rad etilgan"}
        </span>
      </div>

      {/* Asosiy ma'lumotlar */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Rasm + ma'lumotlar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
          {/* Rasm */}
          <div className="p-6 flex items-center justify-center bg-gray-50">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`Tekshiruv #${log.id}`}
                className="max-w-full max-h-64 rounded-lg border border-gray-200 shadow-sm object-contain"
              />
            ) : (
              <div className="w-full h-48 flex items-center justify-center text-gray-300">
                <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            )}
          </div>

          {/* Chap ma'lumotlar */}
          <div className="p-6 space-y-5">
            <InfoRow label="Foydalanuvchi" value={log.username} />
            <InfoRow label="Foydalanuvchi ID" value={`#${log.user_id}`} />
            <InfoRow label="Sana va vaqt" value={formatDate(log.timestamp)} />
            <InfoRow label="Kiritilgan yosh" value={`${log.input_age} yosh`} />
          </div>

          {/* O'ng ma'lumotlar */}
          <div className="p-6 space-y-5">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Yuz aniqlash</p>
              <div className="flex items-center gap-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    log.detection ? "bg-green-500" : "bg-red-400"
                  }`}
                />
                <span className={`text-sm font-medium ${log.detection ? "text-green-700" : "text-red-600"}`}>
                  {log.detection ? "Aniqlandi" : "Topilmadi"}
                </span>
              </div>
            </div>

            <InfoRow
              label="Rasm o'lchami"
              value={`${log.image_width} x ${log.image_height} px`}
              mono
            />

            <InfoRow
              label="Fayl hajmi"
              value={formatBytes(log.file_size_bytes)}
            />

            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Orqa fon rangi</p>
              {bgColorRgb ? (
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-lg border border-gray-200 shadow-sm"
                    style={{ backgroundColor: `rgb(${bgColorRgb.join(",")})` }}
                  />
                  <span className="text-sm font-mono text-gray-700">
                    RGB({bgColorRgb.join(", ")})
                  </span>
                </div>
              ) : (
                <span className="text-sm text-gray-400">Mavjud emas</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Rad etilish sabablari */}
      {errorLines.length > 0 && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-red-800 mb-3 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            Rad etilish sabablari
          </h3>
          <ul className="space-y-2">
            {errorLines.map((msg, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                <span className="text-red-400 mt-0.5 flex-shrink-0">&#x2022;</span>
                {msg}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Muvaffaqiyatli natija */}
      {log.success && (
        <div className="mt-6 bg-green-50 border border-green-200 rounded-2xl p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white text-lg flex-shrink-0">
              &#x2713;
            </div>
            <div>
              <p className="font-semibold text-green-800">Barcha tekshiruvlar muvaffaqiyatli</p>
              <p className="text-sm text-green-600 mt-0.5">Rasm sertifikat uchun yaroqli deb topilgan</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-sm font-medium text-gray-800 ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </div>
  );
}
