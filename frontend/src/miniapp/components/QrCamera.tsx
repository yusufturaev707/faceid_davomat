/**
 * Ilova ichidagi jonli kamera — ID-karta orqasidagi QR kodni o'qish uchun.
 *
 * Ikki rejimda ishlaydi (qurilmaga qarab, ikkalasi ham bir ekranda):
 *   - **avtomatik** — `BarcodeDetector` bo'lsa kadrlar jonli tekshiriladi va
 *     ID-karta QR'i ramkaga tushishi bilan o'zi o'qiladi (serverga bormasdan);
 *   - **suratga olish** — operator tugmani bosadi, kadr backendga yuboriladi
 *     va u yerda zxing-cpp bilan dekodlanadi (iOS'da yagona yo'l).
 *
 * Kamera ochilmasa (ruxsat yo'q, HTTP, kamera band) — `onUnavailable` orqali
 * chaqiruvchiga xabar beriladi, u tizim kamerasi/galereyaga tushiradi.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { telegram } from "../telegram";
import { captureVideoFrame, QR_IMAGE_OPTIONS, type PreparedImage } from "../utils/image";
import {
  cameraErrorMessage,
  cameraUnavailableReason,
  createQrDetector,
  findIdCardQr,
  stopStream,
} from "../utils/qr-scanner";
import { Camera, Flashlight, QrCode } from "./icons";
import { Button, Notice, Spinner } from "./ui";

/** Jonli dekodlash chastotasi — bir kadr ~10–30 ms, 250 ms batareyani ayamaydi. */
const SCAN_INTERVAL_MS = 250;

interface TorchState {
  available: boolean;
  on: boolean;
}

export function QrCamera({
  busy,
  notice,
  onQrText,
  onCapture,
  onUnavailable,
  onCancel,
}: {
  /** Tashqarida so'rov ketyapti — tugmalar bloklanadi, skanerlash to'xtaydi. */
  busy: boolean;
  /** Oxirgi xato (server QR'ni o'qiy olmadi) — kamera ochiq qoladi. */
  notice: string | null;
  /** Jonli detektor ID-karta QR matnini o'qidi. */
  onQrText: (text: string) => void;
  /** Operator kadrni suratga oldi — backend dekodlaydi. */
  onCapture: (image: PreparedImage) => void;
  /** Kamerani umuman ochib bo'lmadi. */
  onUnavailable: (message: string) => void;
  onCancel: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [liveScan, setLiveScan] = useState(false);
  const [torch, setTorch] = useState<TorchState>({ available: false, on: false });
  const [frameError, setFrameError] = useState<string | null>(null);

  // Skanerlash sikli useEffect'dan tashqarida o'zgaradigan qiymatlarni
  // ref orqali o'qiydi — aks holda har bosishda sikl qayta ishga tushardi.
  const busyRef = useRef(busy);
  busyRef.current = busy;
  const onQrTextRef = useRef(onQrText);
  onQrTextRef.current = onQrText;
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;

  // Matn yuborilgach sikl to'xtaydi. So'rov tugagach kamera hali ochiq bo'lsa —
  // demak backend QR'ni rad etdi: skanerlash davom etadi, lekin o'sha matn
  // qora ro'yxatga tushadi (bir xil yaroqsiz QR rate limitni yeb qo'ymasin).
  const sentRef = useRef<string | null>(null);
  const rejectedRef = useRef<Set<string>>(new Set());
  const pausedRef = useRef(false);
  const wasBusyRef = useRef(busy);

  useEffect(() => {
    const wasBusy = wasBusyRef.current;
    wasBusyRef.current = busy;
    if (!wasBusy || busy || sentRef.current === null) return;
    rejectedRef.current.add(sentRef.current);
    sentRef.current = null;
    pausedRef.current = false;
  }, [busy]);

  // ── Kamerani ochish ───────────────────────────────────────
  useEffect(() => {
    const unavailable = cameraUnavailableReason();
    if (unavailable) {
      onUnavailableRef.current(unavailable);
      return;
    }

    let cancelled = false;
    const open = async () => {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          // ID-karta orqa kamerada o'qiladi; `ideal` — old kamerali
          // noutbukda ham oqim beriladi (`exact` bo'lsa xato qaytardi).
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
      } catch (err) {
        if (!cancelled) onUnavailableRef.current(cameraErrorMessage(err));
        return;
      }
      if (cancelled) {
        stopStream(stream);
        return;
      }

      streamRef.current = stream;
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        // iOS'da `play()` promise'i rad etilishi mumkin — `autoplay` atributi
        // baribir oqimni ko'rsatadi, shuning uchun xatoni yutamiz.
        try {
          await video.play();
        } catch {
          /* ignoriya */
        }
      }

      const track = stream.getVideoTracks()[0];
      const caps = track?.getCapabilities?.() as { torch?: boolean } | undefined;
      if (!cancelled) {
        setTorch({ available: !!caps?.torch, on: false });
        setReady(true);
      }
    };

    void open();
    return () => {
      cancelled = true;
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  // ── Jonli dekodlash (BarcodeDetector bo'lsa) ──────────────
  useEffect(() => {
    if (!ready) return;
    let stopped = false;
    let timer = 0;

    const start = async () => {
      const detector = await createQrDetector();
      if (!detector || stopped) return;
      setLiveScan(true);

      const tick = async () => {
        if (stopped) return;
        const video = videoRef.current;
        if (video && video.readyState >= 2 && !busyRef.current && !pausedRef.current) {
          try {
            const match = findIdCardQr(await detector.detect(video), rejectedRef.current);
            if (match && !stopped) {
              pausedRef.current = true;
              sentRef.current = match;
              telegram.haptic("success");
              onQrTextRef.current(match);
              return;
            }
          } catch {
            /* kadr o'qilmadi — keyingisida qayta urinamiz */
          }
        }
        timer = window.setTimeout(() => void tick(), SCAN_INTERVAL_MS);
      };
      void tick();
    };

    void start();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [ready]);

  // ── Amallar ───────────────────────────────────────────────
  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    try {
      setFrameError(null);
      onCapture(captureVideoFrame(video, QR_IMAGE_OPTIONS));
    } catch (err) {
      setFrameError((err as Error).message);
    }
  }, [onCapture]);

  const toggleTorch = useCallback(async () => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return;
    const next = !torch.on;
    try {
      // `torch` hali standart TypeScript tiplarida yo'q — brauzerlar qo'llaydi.
      await track.applyConstraints({ advanced: [{ torch: next }] } as unknown as MediaTrackConstraints);
      setTorch({ available: true, on: next });
    } catch {
      // Qurilma chiroqni qo'llab-quvvatlashini e'lon qilgan, lekin yoqolmadi.
      setTorch({ available: false, on: false });
    }
  }, [torch.on]);

  const hint = busy
    ? "Pasport ma'lumotlari o'qilmoqda..."
    : liveScan
      ? "QR kodni ramka ichiga joylang — o'zi o'qiladi."
      : "QR kodni ramka ichiga joylab, «Suratga olish» tugmasini bosing.";

  return (
    <>
      <div className="overflow-hidden rounded-2xl bg-black">
        <div className="relative aspect-[4/3] w-full">
          <video
            ref={videoRef}
            playsInline
            muted
            autoPlay
            className="h-full w-full object-cover"
          />

          {!ready && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black text-white/80">
              <Spinner />
              <p className="text-[14px]">Kamera ochilmoqda...</p>
            </div>
          )}

          {ready && (
            <>
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="qr-frame relative h-[68%] w-[78%]">
                  {liveScan && !busy && <span className="qr-scanline" />}
                </div>
              </div>
              <p className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-4 pb-3 pt-8 text-center text-[13px] leading-snug text-white">
                {hint}
              </p>
              {torch.available && (
                <button
                  type="button"
                  aria-label={torch.on ? "Chiroqni o'chirish" : "Chiroqni yoqish"}
                  onClick={() => void toggleTorch()}
                  className={`absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full backdrop-blur ${
                    torch.on ? "bg-white text-black" : "bg-black/45 text-white"
                  }`}
                >
                  <Flashlight width={20} height={20} />
                </button>
              )}
              {busy && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/45 text-white">
                  <Spinner />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {(notice || frameError) && (
        <Notice tone="warning" title="QR o'qilmadi">
          {frameError || notice}
        </Notice>
      )}

      <Button onClick={capture} loading={busy} disabled={!ready} icon={<Camera width={20} height={20} />}>
        Suratga olish
      </Button>

      {liveScan && !busy && (
        <p className="flex items-center justify-center gap-2 text-[13px] text-tg-hint">
          <QrCode width={14} height={14} />
          Avtomatik skanerlash yoqilgan
        </p>
      )}

      <Button variant="plain" onClick={onCancel} disabled={busy}>
        Kamerani yopish
      </Button>
    </>
  );
}
