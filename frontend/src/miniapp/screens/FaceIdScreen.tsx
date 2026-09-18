/**
 * Face ID: pasport → selfi → natija → davomatga qo'shish.
 *
 * Bot'dagi oqim bilan bir xil, qo'shimchalar:
 *  - ID-karta QR'i uch yo'l bilan o'qiladi: ilova ichidagi jonli kamera
 *    (`components/QrCamera`), Telegram native skaneri va tayyor rasm;
 *  - natijada GTSP pasport rasmi va selfi yonma-yon ko'rinadi — operator ko'z bilan
 *    ham tasdiqlaydi;
 *  - "Keyingi talabgor" — navbatdagi talabgorga bir bosishda o'tish.
 */

import { useRef, useState, type ReactElement, type RefObject } from "react";
import { api, ApiError } from "../api";
import { Camera, ImageIcon, Pencil, QrCode, ScanFace } from "../components/icons";
import { QrCamera } from "../components/QrCamera";
import { StudentSlotSection } from "../components/StudentSlot";
import {
  Button,
  Card,
  DetailRow,
  MainButton,
  Notice,
  ProgressBar,
  Screen,
  Section,
  Segmented,
  Spinner,
  TextField,
  useToast,
} from "../components/ui";
import { useApp } from "../context";
import { useBackHandler } from "../navigation";
import { telegram } from "../telegram";
import type {
  FaceVerifyResponse,
  MarkAttendanceResponse,
  PassportData,
  ReadySession,
  SmenaInfo,
} from "../types";
import { formatDay } from "../utils/format";
import { prepareImage, QR_IMAGE_OPTIONS, SELFIE_OPTIONS, type PreparedImage } from "../utils/image";
import {
  isValidJshshir,
  looksLikeIdCardQr,
  parsePassport,
  sanitizeJshshirInput,
  sanitizePassportInput,
} from "../utils/passport";

type Step = "passport" | "selfie" | "result";
type PassportMode = "qr" | "manual";

export function FaceIdScreen({ session, smena }: { session: ReadySession; smena: SmenaInfo }) {
  const { region } = useApp();
  const toast = useToast();
  const [step, setStep] = useState<Step>("passport");
  const [passport, setPassport] = useState<PassportData | null>(null);
  const [selfie, setSelfie] = useState<PreparedImage | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<FaceVerifyResponse | null>(null);
  const [marking, setMarking] = useState(false);
  const [attendance, setAttendance] = useState<MarkAttendanceResponse | null>(null);

  useBackHandler(() => {
    if (verifying || marking) return true;
    if (step === "result" && !attendance) {
      setResult(null);
      setStep("selfie");
      return true;
    }
    if (step === "selfie") {
      setStep("passport");
      return true;
    }
    return false;
  });

  const nextStudent = () => {
    setPassport(null);
    setSelfie(null);
    setResult(null);
    setAttendance(null);
    setStep("passport");
    window.scrollTo(0, 0);
  };

  const verify = async () => {
    if (!passport || !selfie) return;
    setVerifying(true);
    try {
      const response = await api.faceVerify({
        session_id: session.id,
        session_smena_id: smena.id,
        region_id: region.id,
        ...passport,
        selfie_b64: selfie.base64,
      });
      setResult(response);
      setStep("result");
      telegram.haptic(
        response.status === "in_smena" && response.verified
          ? "success"
          : response.status === "in_smena" || response.status === "no_face"
            ? "warning"
            : "error",
      );
      window.scrollTo(0, 0);
    } catch (err) {
      telegram.haptic("error");
      toast((err as Error).message, "destructive");
    } finally {
      setVerifying(false);
    }
  };

  const markAttendance = async () => {
    if (!result?.verify_ticket || !selfie) return;
    setMarking(true);
    try {
      const response = await api.markAttendance(result.verify_ticket, selfie.base64);
      setAttendance(response);
      telegram.haptic(response.status === "ok" ? "success" : "warning");
      window.scrollTo(0, 0);
    } catch (err) {
      telegram.haptic("error");
      const message = (err as Error).message;
      toast(message, "destructive");
      // Chipta muddati o'tgan — selfi saqlanadi, operator faqat qayta tekshiradi.
      if (err instanceof ApiError && err.status === 400) {
        setResult(null);
        setStep("selfie");
      }
    } finally {
      setMarking(false);
    }
  };

  return (
    <Screen title="Face ID" subtitle={`${smena.smena_name} • ${formatDay(smena.day)}`}>
      {step === "passport" && (
        <PassportStep
          initial={passport}
          onResolved={(data) => {
            setPassport(data);
            setSelfie(null);
            setStep("selfie");
            window.scrollTo(0, 0);
          }}
        />
      )}

      {step === "selfie" && passport && (
        <SelfieStep
          passport={passport}
          selfie={selfie}
          verifying={verifying}
          onSelfie={setSelfie}
          onEditPassport={() => setStep("passport")}
          onVerify={verify}
        />
      )}

      {step === "result" && result && passport && (
        <ResultStep
          result={result}
          passport={passport}
          selfie={selfie}
          attendance={attendance}
          marking={marking}
          onMark={markAttendance}
          onRetakeSelfie={() => {
            setSelfie(null);
            setResult(null);
            setStep("selfie");
          }}
          onEditPassport={() => {
            setResult(null);
            setStep("passport");
          }}
          onNext={nextStudent}
        />
      )}
    </Screen>
  );
}

// ─────────────────────────────────────────────────────────────
// 1. Pasport
// ─────────────────────────────────────────────────────────────

function PassportStep({
  initial,
  onResolved,
}: {
  initial: PassportData | null;
  onResolved: (data: PassportData) => void;
}) {
  // QR — asosiy yo'l: kamera endi Telegram skaneri yo'q klientlarda ham ishlaydi.
  // Faqat qaytib kelinganda (`initial`) qo'lda kiritish ochiladi — operator
  // o'qilgan ma'lumotni tuzatmoqchi.
  const [mode, setMode] = useState<PassportMode>(initial ? "manual" : "qr");

  return (
    <>
      <Segmented<PassportMode>
        value={mode}
        onChange={setMode}
        options={[
          { value: "qr", label: "ID-karta QR", icon: <QrCode width={18} height={18} /> },
          { value: "manual", label: "Qo'lda", icon: <Pencil width={16} height={16} /> },
        ]}
      />
      {mode === "qr" ? (
        <QrPassport onResolved={onResolved} />
      ) : (
        <ManualPassport initial={initial} onResolved={onResolved} />
      )}
    </>
  );
}

/**
 * ID-karta QR — uchta manba bir ekranda:
 *   1. ilova ichidagi jonli kamera (`QrCamera`) — avtomatik o'qish yoki surat;
 *   2. Telegram native skaneri — mobil klientlarda eng tezi;
 *   3. tayyor rasm — galereyadan yoki tizim kamerasidan (jonli kamera
 *      ochilmagan qurilmalarda zaxira).
 */
function QrPassport({ onResolved }: { onResolved: (data: PassportData) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [camera, setCamera] = useState(false);
  const [cameraBlocked, setCameraBlocked] = useState<string | null>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const systemCameraInput = useRef<HTMLInputElement>(null);

  /** `keepCamera` — kamera ochiq qolsin (xato bo'lsa operator qayta uriniladi). */
  const resolve = async (request: () => Promise<PassportData>, keepCamera = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await request();
      telegram.haptic("success");
      setCamera(false);
      onResolved(data);
    } catch (err) {
      telegram.haptic("error");
      setError((err as Error).message);
      if (!keepCamera) setCamera(false);
    } finally {
      setLoading(false);
    }
  };

  const scan = () => {
    setError(null);
    telegram.scanQr("ID-karta orqa tomonidagi QR kodni ramkaga joylang", (text) => {
      if (!looksLikeIdCardQr(text)) {
        // Boshqa QR — skaner ochiq qoladi, operator to'g'ri kodga yo'naltiradi.
        telegram.haptic("warning");
        return false;
      }
      void resolve(() => api.passportFromQrText(text));
      return true;
    });
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    await resolve(async () => {
      const image = await prepareImage(file, QR_IMAGE_OPTIONS);
      return api.passportFromQrImage(image.base64);
    });
  };

  const openCamera = () => {
    setError(null);
    setCameraBlocked(null);
    setCamera(true);
  };

  if (camera) {
    return (
      <QrCamera
        busy={loading}
        notice={error}
        onQrText={(text) => void resolve(() => api.passportFromQrText(text), true)}
        onCapture={(image) => void resolve(() => api.passportFromQrImage(image.base64), true)}
        onUnavailable={(message) => {
          setCamera(false);
          setCameraBlocked(message);
        }}
        onCancel={() => {
          setCamera(false);
          setError(null);
        }}
      />
    );
  }

  return (
    <>
      <Card className="flex flex-col items-center gap-3 py-6 text-center">
        <span className="tg-tint flex h-16 w-16 items-center justify-center rounded-2xl text-tg-button">
          {loading ? <Spinner /> : <QrCode width={32} height={32} />}
        </span>
        <p className="text-[15px] leading-snug text-tg-hint">
          {loading
            ? "Pasport ma'lumotlari o'qilmoqda..."
            : "ID-karta orqa tomonidagi QR koddan seriya, raqam va JShShIR avtomatik o'qiladi."}
        </p>
      </Card>

      {error && <Notice tone="destructive" title="QR o'qilmadi">{error}</Notice>}
      {cameraBlocked && (
        <Notice tone="warning" title="Kamera ochilmadi">{cameraBlocked}</Notice>
      )}

      {/* Kamera bloklangan bo'lsa asosiy amal tizim kamerasiga o'tadi, lekin
          jonli kamerani qayta ochish imkoni qoladi — ruxsat keyin berilishi mumkin. */}
      <div className="space-y-3">
        <Button
          variant={cameraBlocked ? "secondary" : "primary"}
          onClick={openCamera}
          disabled={loading}
          icon={<Camera width={20} height={20} />}
        >
          {cameraBlocked ? "Kamerani qayta ochish" : "Kamerani ochish"}
        </Button>
        {telegram.canScanQr && (
          <Button
            variant="secondary"
            onClick={scan}
            disabled={loading}
            icon={<QrCode width={20} height={20} />}
          >
            Telegram skaneri
          </Button>
        )}
        <Button
          variant={cameraBlocked ? "primary" : "secondary"}
          onClick={() => systemCameraInput.current?.click()}
          disabled={loading}
          icon={<Camera width={20} height={20} />}
        >
          Suratga olish (tizim kamerasi)
        </Button>
        <Button
          variant="secondary"
          onClick={() => galleryInput.current?.click()}
          disabled={loading}
          icon={<ImageIcon width={20} height={20} />}
        >
          Tayyor rasmni yuklash
        </Button>
      </div>

      <input
        ref={systemCameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          void onFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <input
        ref={galleryInput}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          void onFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </>
  );
}

function ManualPassport({
  initial,
  onResolved,
}: {
  initial: PassportData | null;
  onResolved: (data: PassportData) => void;
}) {
  const [passportRaw, setPassportRaw] = useState(initial ? `${initial.ps_ser}${initial.ps_num}` : "");
  const [jshshir, setJshshir] = useState(initial?.jshshir ?? "");
  const [touched, setTouched] = useState(false);

  const parsed = parsePassport(passportRaw);
  const jshshirValid = isValidJshshir(jshshir);

  const submit = () => {
    setTouched(true);
    if (parsed && jshshirValid) onResolved({ ...parsed, jshshir });
  };

  return (
    <>
      <Section footer="Seriya va raqam birga: 2 ta harf + 7 ta raqam. Kirillcha harflar avtomatik lotinga o'giriladi.">
        <TextField
          label="Pasport seriya va raqami"
          value={passportRaw}
          onChange={(v) => setPassportRaw(sanitizePassportInput(v))}
          placeholder="AD1234567"
          error={touched && !parsed ? "Format: 2 ta harf + 7 ta raqam (masalan, AD1234567)" : null}
        />
        <TextField
          label="JShShIR (PINFL)"
          value={jshshir}
          onChange={(v) => setJshshir(sanitizeJshshirInput(v))}
          placeholder="14 ta raqam"
          inputMode="numeric"
          hint={`${jshshir.length}/14`}
          error={touched && !jshshirValid ? "JShShIR 14 ta raqamdan iborat bo'lishi kerak" : null}
          onEnter={submit}
        />
      </Section>
      <MainButton text="Davom etish" onClick={submit} disabled={!parsed || !jshshirValid} />
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// 2. Selfi
// ─────────────────────────────────────────────────────────────

function PassportSummary({ passport, onEdit }: { passport: PassportData; onEdit?: () => void }) {
  return (
    <Section
      title="Pasport"
      footer={
        onEdit && (
          <button type="button" onClick={onEdit} className="font-medium text-tg-link">
            Pasport ma'lumotlarini o'zgartirish
          </button>
        )
      }
    >
      <DetailRow label="Seriya va raqam" value={`${passport.ps_ser}${passport.ps_num}`} mono />
      <DetailRow label="JShShIR" value={passport.jshshir} mono />
    </Section>
  );
}

function SelfieStep({
  passport,
  selfie,
  verifying,
  onSelfie,
  onEditPassport,
  onVerify,
}: {
  passport: PassportData;
  selfie: PreparedImage | null;
  verifying: boolean;
  onSelfie: (image: PreparedImage | null) => void;
  onEditPassport: () => void;
  onVerify: () => void;
}) {
  const toast = useToast();
  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const [processing, setProcessing] = useState(false);

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    setProcessing(true);
    try {
      onSelfie(await prepareImage(file, SELFIE_OPTIONS));
    } catch (err) {
      toast((err as Error).message, "destructive");
    } finally {
      setProcessing(false);
    }
  };

  const fileInput = (ref: RefObject<HTMLInputElement>, capture: boolean) => (
    <input
      ref={ref}
      type="file"
      accept="image/*"
      {...(capture ? { capture: "user" as const } : {})}
      className="hidden"
      onChange={(e) => {
        void onFile(e.target.files?.[0]);
        e.target.value = "";
      }}
    />
  );

  return (
    <>
      <PassportSummary passport={passport} onEdit={verifying ? undefined : onEditPassport} />

      <Section title="Talabgor selfisi" footer="Yorug' joyda, yuz to'liq va to'g'ri ko'rinadigan qilib oling.">
        {selfie ? (
          <div className="p-3">
            <img
              src={selfie.dataUrl}
              alt="Selfi"
              className="mx-auto aspect-[3/4] w-full max-w-[200px] rounded-xl object-cover"
            />
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 px-4 py-8 text-center text-tg-hint">
            {processing ? <Spinner /> : <ScanFace width={40} height={40} />}
            <p className="text-[14px]">{processing ? "Rasm tayyorlanmoqda..." : "Selfi hali olinmagan"}</p>
          </div>
        )}
      </Section>

      <div className="grid grid-cols-2 gap-3">
        <Button
          variant="secondary"
          onClick={() => cameraInput.current?.click()}
          disabled={verifying || processing}
          icon={<Camera width={20} height={20} />}
        >
          {selfie ? "Qayta olish" : "Kamera"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => galleryInput.current?.click()}
          disabled={verifying || processing}
          icon={<ImageIcon width={20} height={20} />}
        >
          Galereya
        </Button>
      </div>
      {fileInput(cameraInput, true)}
      {fileInput(galleryInput, false)}

      <MainButton
        text={verifying ? "Yuz solishtirilmoqda..." : "Tekshirish"}
        onClick={onVerify}
        disabled={!selfie || processing}
        loading={verifying}
      />
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// 3. Natija
// ─────────────────────────────────────────────────────────────

function photoSrc(b64: string): string {
  return b64.startsWith("data:") ? b64 : `data:image/jpeg;base64,${b64}`;
}

function VerifyScore({ result, selfie }: { result: FaceVerifyResponse; selfie: PreparedImage | null }) {
  return (
    <Card className="space-y-4">
      {(result.photo_b64 || selfie) && (
        <div className="grid grid-cols-2 gap-3">
          {[
            { src: result.photo_b64 ? photoSrc(result.photo_b64) : null, label: "Pasport (GTSP)" },
            { src: selfie?.dataUrl ?? null, label: "Selfi" },
          ].map(({ src, label }) => (
            <figure key={label} className="space-y-1.5">
              {src ? (
                <img src={src} alt={label} className="aspect-[3/4] w-full rounded-xl bg-tg-secondary object-cover" />
              ) : (
                <div className="aspect-[3/4] w-full rounded-xl bg-tg-secondary" />
              )}
              <figcaption className="text-center text-[12px] text-tg-hint">{label}</figcaption>
            </figure>
          ))}
        </div>
      )}
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-[14px] text-tg-hint">Yuz o'xshashligi</span>
          <span
            className={`text-[22px] font-bold tabular-nums ${result.verified ? "text-tg-success" : "text-tg-destructive"}`}
          >
            {result.score}%
          </span>
        </div>
        <div className="mt-2">
          <ProgressBar
            value={result.score}
            tone={result.verified ? "success" : "destructive"}
            marker={result.threshold}
          />
        </div>
        <p className="mt-1.5 text-[12px] text-tg-hint">Tasdiqlash chegarasi: {result.threshold}%</p>
      </div>
    </Card>
  );
}

function AttendanceNotice({ attendance, score }: { attendance: MarkAttendanceResponse; score: number }) {
  switch (attendance.status) {
    case "ok":
      return (
        <Notice tone="success" title="Davomatga qo'shildi">
          {`${attendance.message}\nYuz o'xshashligi: ${score}%`}
        </Notice>
      );
    case "already_entered":
      return <Notice tone="accent" title="Talabgor allaqachon kirgan">{attendance.message}</Notice>;
    case "applied":
      return <Notice tone="warning" title="Talabgor arizali">{attendance.message}</Notice>;
    case "not_found":
      return <Notice tone="destructive" title="Talabgor topilmadi">{attendance.message}</Notice>;
    default:
      return <Notice tone="destructive" title="Xatolik">{attendance.message}</Notice>;
  }
}

function ResultStep({
  result,
  passport,
  selfie,
  attendance,
  marking,
  onMark,
  onRetakeSelfie,
  onEditPassport,
  onNext,
}: {
  result: FaceVerifyResponse;
  passport: PassportData;
  selfie: PreparedImage | null;
  attendance: MarkAttendanceResponse | null;
  marking: boolean;
  onMark: () => void;
  onRetakeSelfie: () => void;
  onEditPassport: () => void;
  onNext: () => void;
}) {
  const { status, slot, message } = result;
  const canMark = status === "in_smena" && result.can_attend && !!result.verify_ticket && !attendance;

  let notice: ReactElement;
  switch (status) {
    case "in_smena":
      notice = result.verified ? (
        <Notice tone="success" title="Yuz tasdiqlandi">{message}</Notice>
      ) : (
        <Notice tone="destructive" title="Yuz tasdiqlanmadi">{message}</Notice>
      );
      break;
    case "wrong_slot":
      notice = (
        <Notice tone="warning" title="Talabgor bu smenada yo'q">
          {`${message}\nBu holatda davomatga qo'shib bo'lmaydi.`}
        </Notice>
      );
      break;
    case "not_in_session":
      notice = (
        <Notice tone="destructive" title="Talabgor bu test tadbirida yo'q">
          {`JShShIR: ${passport.jshshir}\n${message}`}
        </Notice>
      );
      break;
    case "wrong_passport":
      notice = <Notice tone="destructive" title="Pasport ma'lumotlari xato">{message}</Notice>;
      break;
    case "no_face":
      notice = (
        <Notice tone="warning" title="Yuz aniqlanmadi">
          {`${message}\nYorug' joyda, yuzni to'liq ko'rsatib qayta suratga oling.`}
        </Notice>
      );
      break;
    case "applied":
      notice = <Notice tone="warning" title="Talabgor arizali">{message}</Notice>;
      break;
    default:
      notice = <Notice tone="destructive" title="Xatolik">{message || status}</Notice>;
  }

  const canRetakeSelfie = !attendance && (status === "in_smena" || status === "no_face");
  const canFixPassport = !attendance && (status === "wrong_passport" || status === "not_in_session");

  return (
    <>
      {attendance ? <AttendanceNotice attendance={attendance} score={result.score} /> : notice}

      {status === "in_smena" && <VerifyScore result={result} selfie={selfie} />}

      {slot && (
        <StudentSlotSection
          slot={slot}
          title={status === "in_smena" ? "Talabgor" : "Talabgorning testdagi joyi"}
        />
      )}
      {status === "in_smena" && result.fio && slot && result.fio !== slot.fio && (
        <p className="-mt-3 px-4 text-[13px] text-tg-hint">GTSP bo'yicha FIO: {result.fio}</p>
      )}
      {!attendance && slot?.is_entered && (
        <Notice tone="accent" title="Talabgor allaqachon davomatga qo'shilgan" />
      )}

      {(canRetakeSelfie || canFixPassport) && (
        <Button
          variant="secondary"
          onClick={canRetakeSelfie ? onRetakeSelfie : onEditPassport}
          disabled={marking}
          icon={canRetakeSelfie ? <Camera width={20} height={20} /> : <Pencil width={18} height={18} />}
        >
          {canRetakeSelfie ? "Qayta suratga olish" : "Pasportni tuzatish"}
        </Button>
      )}

      {canMark && (
        <Button variant="plain" onClick={onNext} disabled={marking}>
          Qo'shmasdan keyingi talabgorga o'tish
        </Button>
      )}

      {canMark ? (
        <MainButton text="Davomatga qo'shish" onClick={onMark} loading={marking} />
      ) : (
        <MainButton text="Keyingi talabgor" onClick={onNext} />
      )}
    </>
  );
}
