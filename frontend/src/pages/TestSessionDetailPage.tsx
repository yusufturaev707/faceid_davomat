import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type {
  PassportUpdateResult,
  PassportUpdateRow,
  SessionStateResponse,
  SmenaResponse,
  StudentResponse,
  TestResponse,
  TestSessionResponse,
} from "../interfaces";
import {
  addSmenaToSessionApi,
  cancelStudentLoadApi,
  changeSessionStateApi,
  deleteTestSessionApi,
  getEmbeddingProgressApi,
  getSessionStatesLookupApi,
  getSessionStudentStatsApi,
  getSmenasLookupApi,
  getStudentLoadProgressApi,
  reloadStudentLoadApi,
  getStudentsApi,
  getTestSessionApi,
  getTestsLookupApi,
  removeSmenaFromSessionApi,
  retryEmbeddingApi,
  updateTestSessionApi,
  uploadStudentImageApi,
  uploadStudentsExcelApi,
  downloadStudentsExcelTemplate,
  updateSessionPassportsApi,
  uploadSessionPassportsExcelApi,
  downloadPassportTemplate,
  fileToBase64,
} from "../api";
import Md3Select from "../components/Md3Select";
import PageLoader from "../components/PageLoader";
import PermissionGate from "../components/PermissionGate";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

export default function TestSessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<TestSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Lookups
  const [states, setStates] = useState<SessionStateResponse[]>([]);
  const [tests, setTests] = useState<TestResponse[]>([]);
  const [smenas, setSmenas] = useState<SmenaResponse[]>([]);

  // State change (stepper)
  const [changingState, setChangingState] = useState(false);
  const [targetStateId, setTargetStateId] = useState<number | null>(null);
  const [loadProgress, setLoadProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("");
  // Student yuklashni bekor qilish
  const [cancellingLoad, setCancellingLoad] = useState(false);
  // Xato bo'lmagan info xabar (masalan, "yuklash bekor qilindi")
  const [stateNotice, setStateNotice] = useState("");
  // DB'ga insert bo'lmagan studentlar (imie + sabab) — yuklash yakunida ko'rsatiladi
  const [failedInserts, setFailedInserts] = useState<
    { imie: string; reason: string }[]
  >([]);
  // O'tkazib yuborilgan (parsing/smena/dublikat) studentlar — yuklash yakunida
  const [skippedStudents, setSkippedStudents] = useState<
    { imie: string; reason: string }[]
  >([]);

  // Edit modal
  const [showEdit, setShowEdit] = useState(false);
  const [editName, setEditName] = useState("");
  const [editTestId, setEditTestId] = useState(0);
  const [editStartDate, setEditStartDate] = useState("");
  const [editFinishDate, setEditFinishDate] = useState("");
  const [editSmPerDay, setEditSmPerDay] = useState(0);
  const [editIsActive, setEditIsActive] = useState(true);
  const [editError, setEditError] = useState("");
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Delete confirm modal
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  // Add smena modal
  const [showAddSmena, setShowAddSmena] = useState(false);
  const [addSmenaId, setAddSmenaId] = useState(0);
  const [addSmenaDay, setAddSmenaDay] = useState("");
  const [addSmenaError, setAddSmenaError] = useState("");
  const [addSmenaSubmitting, setAddSmenaSubmitting] = useState(false);

  // Remove smena confirm
  const [removeSmenaTarget, setRemoveSmenaTarget] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const [removingSmena, setRemovingSmena] = useState(false);

  // Student stats & failed students
  const [studentStats, setStudentStats] = useState<{
    total: number; ready: number; not_ready: number; no_image: number; no_face: number;
  } | null>(null);
  const [failedStudents, setFailedStudents] = useState<StudentResponse[]>([]);
  const [showFailedStudents, setShowFailedStudents] = useState(false);
  const [loadingFailedStudents, setLoadingFailedStudents] = useState(false);
  const [retryingEmbedding, setRetryingEmbedding] = useState(false);
  const [uploadingImageId, setUploadingImageId] = useState<number | null>(null);

  // === Excel upload (state.key=1 → key=2 alternative flow) ===
  const [showExcelUpload, setShowExcelUpload] = useState(false);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelError, setExcelError] = useState<string | null>(null);
  const [excelSubmitting, setExcelSubmitting] = useState(false);
  const [templateDownloading, setTemplateDownloading] = useState(false);

  // === Passport (ps_ser/ps_num) ommaviy yangilash ===
  const [showPassportUpdate, setShowPassportUpdate] = useState(false);
  const [passportMode, setPassportMode] = useState<"paste" | "excel">("paste");
  const [passportPaste, setPassportPaste] = useState("");
  const [passportFile, setPassportFile] = useState<File | null>(null);
  const [passportSubmitting, setPassportSubmitting] = useState(false);
  const [passportError, setPassportError] = useState<string | null>(null);
  const [passportResult, setPassportResult] = useState<PassportUpdateResult | null>(null);
  const [passportTplDownloading, setPassportTplDownloading] = useState(false);

  const fetchSession = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getTestSessionApi(Number(id));
      setSession(data);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchStudentStats = useCallback(async () => {
    if (!id) return;
    try {
      const stats = await getSessionStudentStatsApi(Number(id));
      setStudentStats(stats);
    } catch { /* ignore */ }
  }, [id]);

  const fetchFailedStudents = useCallback(async (sess: TestSessionResponse) => {
    setLoadingFailedStudents(true);
    try {
      const allFailed: StudentResponse[] = [];
      for (const sm of sess.smenas) {
        const res = await getStudentsApi({
          session_smena_id: sm.id,
          is_ready: false,
          per_page: 100,
        });
        allFailed.push(...res.items);
      }
      setFailedStudents(allFailed);
    } catch { /* ignore */ }
    setLoadingFailedStudents(false);
  }, []);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  // Load lookups once
  useEffect(() => {
    Promise.all([
      getSessionStatesLookupApi(),
      getTestsLookupApi(),
      getSmenasLookupApi(),
    ]).then(([s, t, sm]) => {
      setStates(s);
      setTests(t);
      setSmenas(sm);
    });
  }, []);

  // Fetch student stats when session is loaded and state >= 3
  useEffect(() => {
    if (!session || !states.length) return;
    const stateKey = states.find((s) => s.id === session.test_state_id)?.key ?? 0;
    if (stateKey >= 3) {
      fetchStudentStats();
    }
  }, [session?.id, session?.test_state_id, states.length, fetchStudentStats]);

  const [stateError, setStateError] = useState("");

  // Student loading polling — Celery task'dan kelayotgan progressni Redis orqali oqish
  const startStudentLoadPolling = useCallback((sessionId: number) => {
    // "idle" — Redis'da progress yo'q (task hali boshlanmagan, crash bo'lgan
    // yoki TTL tugagan). Endpoint .delay() bilan birga darhol "processing"
    // yozadi, shuning uchun normal holatda idle deyarli kelmaydi. Bir necha
    // marta ketma-ket idle bo'lsa — task ishga tushmagan deb hisoblab,
    // spinnerni abadiy aylantirmasdan to'xtatamiz.
    let consecutiveIdle = 0;
    const poll = setInterval(async () => {
      try {
        const p = await getStudentLoadProgressApi(sessionId);

        if (p.status === "idle") {
          consecutiveIdle += 1;
          if (consecutiveIdle >= 5) {
            clearInterval(poll);
            setLoadProgress(0);
            setProgressLabel("");
            setStateError(
              "Talabalar yuklash jarayoni boshlanmadi (navbat/worker ishlamayapti yoki vaqt tugadi). Iltimos, qayta urinib ko'ring.",
            );
            try {
              const refreshed = await getTestSessionApi(sessionId);
              setSession(refreshed);
            } catch {
              /* ignore */
            }
            setChangingState(false);
            setTargetStateId(null);
          }
          return;
        }
        consecutiveIdle = 0;

        // Progress bar — agar total ma'lum bo'lsa aniq foiz, aks holda
        // sahifalar bo'yicha. Backend kumulyativ totalCount yig'ib boradi,
        // shuning uchun foiz faqat o'sib boradi va 100%'dan oshmaydi.
        if (p.percent > 0) {
          setLoadProgress(Math.min(100, p.percent));
        } else if (p.current > 0) {
          // Indeterminate — sahifa progressiga qarab oshiramiz
          setLoadProgress((prev) => Math.min(95, prev + 1));
        }

        // Label: "X / TOTAL ta yuklandi" — TOTAL barcha kunlardagi
        // totalCount'lar yig'indisi (discovery fazasidan keyin ma'lum).
        const labelParts: string[] = [];
        if (p.total > 0) {
          labelParts.push(
            `${p.current.toLocaleString("uz-UZ")} / ${p.total.toLocaleString("uz-UZ")} ta yuklandi`,
          );
        } else if (p.current > 0) {
          labelParts.push(`${p.current.toLocaleString("uz-UZ")} ta yuklandi`);
        }
        if (p.skipped > 0) labelParts.push(`${p.skipped.toLocaleString("uz-UZ")} ta o'tkazildi`);
        if (p.message) labelParts.push(p.message);
        setProgressLabel(
          labelParts.length ? `Talabalar: ${labelParts.join(" · ")}` : "Talabalar yuklanmoqda...",
        );

        if (p.status === "completed") {
          clearInterval(poll);
          setCancellingLoad(false);
          setFailedInserts(p.failed_items || []);
          setSkippedStudents(p.skipped_items || []);
          setLoadProgress(100);
          const finalParts = [`Tayyor: ${p.current.toLocaleString("uz-UZ")} ta talaba yuklandi`];
          if (p.total > 0 && p.total !== p.current) {
            finalParts.push(`(${p.total.toLocaleString("uz-UZ")} ta umumiy)`);
          }
          if (p.skipped > 0) {
            finalParts.push(`${p.skipped.toLocaleString("uz-UZ")} ta o'tkazib yuborildi`);
          }
          setProgressLabel(finalParts.join(" · "));
          setTimeout(async () => {
            try {
              const refreshed = await getTestSessionApi(sessionId);
              setSession(refreshed);
            } catch { /* ignore */ }
            setChangingState(false);
            setTargetStateId(null);
            setLoadProgress(0);
            setProgressLabel("");
          }, 800);
        } else if (p.status === "error") {
          clearInterval(poll);
          setLoadProgress(0);
          setProgressLabel("");
          setCancellingLoad(false);
          setFailedInserts(p.failed_items || []);
          setSkippedStudents(p.skipped_items || []);
          setStateError(p.message || "Talabalarni yuklashda xatolik yuz berdi");
          // Sessiya state'i backend tomonida rollback qilingan — qayta yuklash
          try {
            const refreshed = await getTestSessionApi(sessionId);
            setSession(refreshed);
          } catch { /* ignore */ }
          setChangingState(false);
          setTargetStateId(null);
        } else if (p.status === "cancelled") {
          // Foydalanuvchi bekor qildi — backend state'ni qaytarib, yarim
          // yuklangan studentlarni tozalab bo'ldi. Bu xato emas — info banner.
          clearInterval(poll);
          setLoadProgress(0);
          setProgressLabel("");
          setCancellingLoad(false);
          setStateNotice(p.message || "Yuklash bekor qilindi");
          try {
            const refreshed = await getTestSessionApi(sessionId);
            setSession(refreshed);
          } catch { /* ignore */ }
          setChangingState(false);
          setTargetStateId(null);
        }
      } catch {
        // Polling xatosi — keyingi cikl'da qayta urinamiz
      }
    }, 1500);
    return poll;
  }, []);

  // Embedding polling funksiyasi — handleNextStep va useEffect da ishlatiladi
  const startEmbeddingPolling = useCallback((sessionId: number) => {
    // Backend Redis kalitiga TTL qo'yadi va task crash bo'lsa "error" holatini
    // saqlaydi. TTL tugab "idle" qaytsa (yoki Redis o'chsa) — ortiqcha kutmasdan
    // to'xtatamiz. consecutiveIdle counter false-positive lardan himoya qiladi.
    let consecutiveIdle = 0;
    const poll = setInterval(async () => {
      try {
        const p = await getEmbeddingProgressApi(sessionId);

        if (p.status === "idle") {
          consecutiveIdle += 1;
          // ~6s davomida idle bo'lsa — task crash yoki TTL tugagan deb hisoblaymiz
          if (consecutiveIdle >= 4) {
            clearInterval(poll);
            setStateError(
              "Embedding jarayoni to'xtab qoldi (vaqt tugadi yoki task ishdan chiqdi). Iltimos, qayta urinib ko'ring.",
            );
            setChangingState(false);
            setTargetStateId(null);
            setLoadProgress(0);
            setProgressLabel("");
          }
          return;
        }
        consecutiveIdle = 0;

        if (p.total > 0) {
          setLoadProgress(p.percent);
          const parts: string[] = [`${p.current}/${p.total}`];
          if (p.success > 0) parts.push(`${p.success} tayyor`);
          if (p.no_image > 0) parts.push(`${p.no_image} rasmsiz`);
          if (p.no_face > 0) parts.push(`${p.no_face} yuzsiz`);
          if (p.errors > 0) parts.push(`${p.errors} xato`);
          setProgressLabel(`Embedding: ${parts.join(", ")}`);
        }

        if (p.status === "error") {
          clearInterval(poll);
          const message =
            (p as { message?: string }).message ||
            "Embedding jarayonida kutilmagan xatolik yuz berdi";
          setStateError(message);
          setChangingState(false);
          setTargetStateId(null);
          setLoadProgress(0);
          setProgressLabel("");
          // Sessiya holatini yangilash — backend rollback qilgan bo'lishi mumkin
          try {
            const refreshed = await getTestSessionApi(sessionId);
            setSession(refreshed);
          } catch { /* ignore */ }
          return;
        }

        if (p.status === "completed" || p.status === "completed_with_errors") {
          clearInterval(poll);
          setLoadProgress(100);

          const failed = (p.no_image || 0) + (p.no_face || 0) + (p.errors || 0);
          if (failed > 0) {
            const msgs: string[] = [];
            if (p.no_image > 0) msgs.push(`${p.no_image} ta studentda rasm topilmadi`);
            if (p.no_face > 0) msgs.push(`${p.no_face} ta studentda yuz aniqlanmadi`);
            if (p.errors > 0) msgs.push(`${p.errors} ta studentda xatolik`);
            setProgressLabel(`Embedding tugadi: ${msgs.join(", ")}`);
          } else {
            setProgressLabel("Embedding muvaffaqiyatli tugadi!");
          }

          setTimeout(async () => {
            try {
              const refreshed = await getTestSessionApi(sessionId);
              setSession(refreshed);
              // Student stats yangilash
              const stats = await getSessionStudentStatsApi(sessionId);
              setStudentStats(stats);
            } catch { /* ignore */ }
            setChangingState(false);
            setTargetStateId(null);
            setLoadProgress(0);
            setProgressLabel("");
          }, 1000);
        }
      } catch {
        // polling xatosi — davom etamiz
      }
    }, 1500);
    return poll;
  }, []);

  // Sahifa yuklanganda embedding davom etayotganini tekshirish
  useEffect(() => {
    if (!session || !states.length || changingState) return;
    const currentState = states.find((s) => s.id === session.test_state_id);
    if (!currentState || currentState.key !== 3) return;

    let pollId: ReturnType<typeof setInterval> | null = null;

    getEmbeddingProgressApi(session.id).then((p) => {
      if (p.status === "processing") {
        setChangingState(true);
        setTargetStateId(session.test_state_id);
        setLoadProgress(p.percent);
        setProgressLabel("Embedding davom etmoqda...");
        pollId = startEmbeddingPolling(session.id);
      }
    }).catch(() => { /* ignore */ });

    return () => { if (pollId) clearInterval(pollId); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id, session?.test_state_id, states.length, startEmbeddingPolling]);

  // Sahifa yuklanganda student loading davom etayotganini tekshirish (state key=2)
  useEffect(() => {
    if (!session || !states.length || changingState) return;
    const currentState = states.find((s) => s.id === session.test_state_id);
    if (!currentState || currentState.key !== 2) return;

    let pollId: ReturnType<typeof setInterval> | null = null;

    getStudentLoadProgressApi(session.id).then((p) => {
      if (p.status === "processing") {
        setChangingState(true);
        setTargetStateId(session.test_state_id);
        setLoadProgress(Math.min(100, Math.max(p.percent, 1)));
        setProgressLabel(p.message || "Talabalar yuklanmoqda...");
        pollId = startStudentLoadPolling(session.id);
      }
    }).catch(() => { /* ignore */ });

    return () => { if (pollId) clearInterval(pollId); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id, session?.test_state_id, states.length, startStudentLoadPolling]);

  // Sorted states by key for stepper
  const sortedStates = [...states].sort((a, b) => a.key - b.key);
  const currentStateKey = sortedStates.find(
    (s) => s.id === session?.test_state_id
  )?.key ?? 0;
  const currentStepIndex = sortedStates.findIndex(
    (s) => s.id === session?.test_state_id
  );

  // Student yuklashni bekor qilish — backend flag qo'yadi, natija ("cancelled")
  // odatdagi progress polling orqali keladi (state rollback + tozalash tugagach).
  const handleCancelLoad = async () => {
    if (!session || cancellingLoad) return;
    setCancellingLoad(true);
    try {
      await cancelStudentLoadApi(session.id);
      setProgressLabel("Bekor qilish so'raldi — jarayon to'xtatilmoqda...");
    } catch (err) {
      setCancellingLoad(false);
      setStateError(extractErrorMessage(err));
    }
  };

  // Resumable qayta yuklash — faqat tugamagan/xato bergan kunlarni qayta yuklaydi.
  const handleReloadLoad = async () => {
    if (!session) return;
    setStateError("");
    setFailedInserts([]);
    setSkippedStudents([]);
    setChangingState(true);
    setTargetStateId(session.test_state_id);
    setLoadProgress(0.5);
    setProgressLabel("Qolgan kunlar qayta yuklanmoqda...");
    try {
      await reloadStudentLoadApi(session.id);
      startStudentLoadPolling(session.id);
    } catch (err) {
      setChangingState(false);
      setTargetStateId(null);
      setStateError(extractErrorMessage(err));
    }
  };

  const handleNextStep = async () => {
    if (!session || currentStepIndex < 0) return;
    const nextState = sortedStates[currentStepIndex + 1];
    if (!nextState) return;

    setChangingState(true);
    setTargetStateId(nextState.id);
    setStateError("");
    setStateNotice("");
    setFailedInserts([]);
    setSkippedStudents([]);
    setLoadProgress(0);
    setProgressLabel("");

    // State 2 (talabalar yuklash) — Celery task, real progress polling
    if (nextState.key === 2) {
      try {
        const updated = await changeSessionStateApi(session.id, nextState.id);
        setSession(updated);
        setProgressLabel("Talabalar yuklash boshlanmoqda...");
        setLoadProgress(0.5);
        startStudentLoadPolling(session.id);
      } catch (err) {
        setChangingState(false);
        setTargetStateId(null);
        setStateError(extractErrorMessage(err));
      }
      return;
    }

    // State 3 (embedding) — Celery task, alohida flow
    if (nextState.key === 3) {
      try {
        const updated = await changeSessionStateApi(session.id, nextState.id);
        setSession(updated);
        // Celery task boshlandi — endi polling boshlaymiz
        setProgressLabel("Embedding boshlanmoqda...");
        setLoadProgress(0.5);
        startEmbeddingPolling(session.id);
      } catch (err) {
        setChangingState(false);
        setTargetStateId(null);
        setStateError(extractErrorMessage(err));
      }
      return;
    }

    // Boshqa statelar uchun (4 — faollashtirish, 5 — yakunlash) umumiy flow
    const labels: Record<number, string> = {
      4: "Sessiya faollashtirilmoqda...",
      5: "Sessiya yakunlanmoqda...",
    };
    setProgressLabel(labels[nextState.key] || "Holat o'zgartirilmoqda...");
    setLoadProgress(5);
    const progressInterval: ReturnType<typeof setInterval> = setInterval(() => {
      setLoadProgress((prev) => {
        if (prev >= 95) return prev;
        return prev + Math.random() * 15 + 10;
      });
    }, 200);

    try {
      const updated = await changeSessionStateApi(session.id, nextState.id);
      clearInterval(progressInterval);
      setLoadProgress(100);
      await new Promise((r) => setTimeout(r, 600));
      setSession(updated);
      setLoadProgress(0);
      setProgressLabel("");
      setTargetStateId(null);
    } catch (err) {
      clearInterval(progressInterval);
      setLoadProgress(0);
      setProgressLabel("");
      setTargetStateId(null);
      setStateError(extractErrorMessage(err));
      try {
        const refreshed = await getTestSessionApi(session.id);
        setSession(refreshed);
      } catch {
        // Qayta yuklash ham xato bo'lsa, hozirgi holatda qolamiz
      }
    } finally {
      setChangingState(false);
    }
  };


  const handleRetryEmbedding = async () => {
    if (!session) return;
    setRetryingEmbedding(true);
    setStateError("");
    try {
      await retryEmbeddingApi(session.id);
      // Celery task boshlandi — polling boshlaymiz
      setChangingState(true);
      setTargetStateId(session.test_state_id);
      setProgressLabel("Qayta embedding boshlanmoqda...");
      setLoadProgress(0.5);
      startEmbeddingPolling(session.id);
    } catch (err) {
      setStateError(extractErrorMessage(err));
    } finally {
      setRetryingEmbedding(false);
    }
  };

  const handleUploadImage = async (studentId: number, file: File) => {
    setUploadingImageId(studentId);
    try {
      const base64 = await fileToBase64(file);
      // data:image/...;base64,XXXXX formatdan faqat base64 qismini olish
      const b64Data = base64.includes(",") ? base64.split(",")[1] : base64;
      await uploadStudentImageApi(studentId, b64Data);
      // Muvaffaqiyatli — ro'yxatni yangilash
      if (session) {
        await fetchFailedStudents(session);
        await fetchStudentStats();
      }
    } catch (err) {
      alert(extractErrorMessage(err));
    } finally {
      setUploadingImageId(null);
    }
  };

  // Excel orqali studentlarni yuklash. Backend Celery task yuradi, biz mavjud
  // student-load polling'ni qayta ishlatamiz — yakunida sessiya state.key=2 ga
  // o'tadi va status badge avtomatik yangilanadi.
  const openExcelUpload = () => {
    setExcelFile(null);
    setExcelError(null);
    setShowExcelUpload(true);
  };

  const handleDownloadTemplate = async () => {
    setTemplateDownloading(true);
    setExcelError(null);
    try {
      await downloadStudentsExcelTemplate();
    } catch (err) {
      setExcelError(extractErrorMessage(err));
    } finally {
      setTemplateDownloading(false);
    }
  };

  const handleExcelUpload = async () => {
    if (!session || !excelFile) return;
    setExcelSubmitting(true);
    setExcelError(null);
    try {
      await uploadStudentsExcelApi(session.id, excelFile);
      // Server qabul qildi — modalni yopib, mavjud progress flow'ni boshlaymiz
      setShowExcelUpload(false);
      setExcelFile(null);
      setChangingState(true);
      setTargetStateId(session.test_state_id);
      setStateError("");
      setLoadProgress(2);
      setProgressLabel("Excel qabul qilindi, qayta ishlanmoqda...");
      startStudentLoadPolling(session.id);
    } catch (err) {
      setExcelError(extractErrorMessage(err));
    } finally {
      setExcelSubmitting(false);
    }
  };

  // --- Passport ommaviy yangilash ---
  const openPassportUpdate = () => {
    setPassportMode("paste");
    setPassportPaste("");
    setPassportFile(null);
    setPassportError(null);
    setPassportResult(null);
    setShowPassportUpdate(true);
  };

  const handlePassportTemplate = async () => {
    setPassportTplDownloading(true);
    setPassportError(null);
    try {
      await downloadPassportTemplate();
    } catch (err) {
      setPassportError(extractErrorMessage(err));
    } finally {
      setPassportTplDownloading(false);
    }
  };

  const handlePassportSubmit = async () => {
    if (!session) return;
    setPassportSubmitting(true);
    setPassportError(null);
    setPassportResult(null);
    try {
      let result: PassportUpdateResult;
      if (passportMode === "excel") {
        if (!passportFile) return;
        result = await uploadSessionPassportsExcelApi(session.id, passportFile);
      } else {
        const rows = parsePastedPassports(passportPaste);
        if (rows.length === 0) {
          setPassportError(
            "Qatorlar topilmadi. Excel'dan jshshir, ps_ser, ps_num ustunlarini nusxalab joylashtiring.",
          );
          return;
        }
        result = await updateSessionPassportsApi(session.id, rows);
      }
      setPassportResult(result);
      // Passport o'zgargach student statistikasi yangilanishi mumkin
      await fetchStudentStats();
    } catch (err) {
      setPassportError(extractErrorMessage(err));
    } finally {
      setPassportSubmitting(false);
    }
  };

  const handlePrevStep = async () => {
    if (!session || currentStateKey !== 5) return;
    const prevState = sortedStates.find((s) => s.key === 4);
    if (!prevState) return;

    setChangingState(true);
    setTargetStateId(prevState.id);
    setStateError("");
    setLoadProgress(5);
    setProgressLabel("Oldingi holatga qaytarilmoqda...");

    const progressInterval = setInterval(() => {
      setLoadProgress((prev) => (prev >= 95 ? prev : prev + Math.random() * 15 + 10));
    }, 200);

    try {
      const updated = await changeSessionStateApi(session.id, prevState.id);
      clearInterval(progressInterval);
      setLoadProgress(100);
      await new Promise((r) => setTimeout(r, 600));
      setSession(updated);
      setLoadProgress(0);
      setProgressLabel("");
      setTargetStateId(null);
    } catch (err) {
      clearInterval(progressInterval);
      setLoadProgress(0);
      setProgressLabel("");
      setTargetStateId(null);
      setStateError(extractErrorMessage(err));
      try {
        const refreshed = await getTestSessionApi(session.id);
        setSession(refreshed);
      } catch { /* ignore */ }
    } finally {
      setChangingState(false);
    }
  };

  const openEditModal = () => {
    if (!session) return;
    setEditName(session.name);
    setEditTestId(session.test_id);
    setEditStartDate(session.start_date);
    setEditFinishDate(session.finish_date);
    setEditSmPerDay(session.count_sm_per_day);
    setEditIsActive(session.is_active);
    setEditError("");
    setShowEdit(true);
  };

  const handleEdit = async () => {
    if (!session) return;
    setEditError("");
    if (!editName.trim()) {
      setEditError("Nom kiritilmagan");
      return;
    }
    if (!editStartDate || !editFinishDate) {
      setEditError("Sanalar kiritilmagan");
      return;
    }
    if (editFinishDate < editStartDate) {
      setEditError("Tugash sanasi boshlanishdan oldin");
      return;
    }
    setEditSubmitting(true);
    try {
      const updated = await updateTestSessionApi(session.id, {
        name: editName.trim(),
        test_id: editTestId,
        start_date: editStartDate,
        finish_date: editFinishDate,
        count_sm_per_day: editSmPerDay,
        is_active: editIsActive,
      });
      setSession(updated);
      setShowEdit(false);
    } catch (err) {
      setEditError(extractErrorMessage(err));
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!session) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteTestSessionApi(session.id);
      navigate("/test-sessions");
    } catch (err) {
      setDeleteError(extractErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const openAddSmena = () => {
    setAddSmenaId(smenas[0]?.id || 0);
    setAddSmenaDay(session?.start_date || "");
    setAddSmenaError("");
    setShowAddSmena(true);
  };

  const handleAddSmena = async () => {
    if (!session) return;
    setAddSmenaError("");
    if (!addSmenaId) {
      setAddSmenaError("Smena tanlanmagan");
      return;
    }
    if (!addSmenaDay) {
      setAddSmenaError("Sana kiritilmagan");
      return;
    }
    setAddSmenaSubmitting(true);
    try {
      await addSmenaToSessionApi(session.id, {
        test_smena_id: addSmenaId,
        day: addSmenaDay,
      });
      setShowAddSmena(false);
      fetchSession();
    } catch (err) {
      setAddSmenaError(extractErrorMessage(err));
    } finally {
      setAddSmenaSubmitting(false);
    }
  };

  const handleRemoveSmena = async () => {
    if (!session || !removeSmenaTarget) return;
    setRemovingSmena(true);
    try {
      await removeSmenaFromSessionApi(session.id, removeSmenaTarget.id);
      setRemoveSmenaTarget(null);
      fetchSession();
    } catch (err) {
      alert(extractErrorMessage(err));
    } finally {
      setRemovingSmena(false);
    }
  };

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString("uz-UZ", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });

  const formatDateTime = (d: string) =>
    new Date(d).toLocaleString("uz-UZ", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (loading) return <PageLoader />;

  if (error || !session) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-10 text-center">
          <p className="text-red-600 dark:text-red-400 font-medium mb-4">
            {error || "Sessiya topilmadi"}
          </p>
          <Link
            to="/test-sessions"
            className="text-primary-600 dark:text-primary-400 hover:underline text-sm"
          >
            Sessiyalarga qaytish
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          to="/test-sessions"
          className="flex items-center gap-1 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          <span className="text-sm">Orqaga</span>
        </Link>
        <div className="flex-1">
          <h2 className="section-title">{session.name}</h2>
          <p className="text-xs text-gray-400 dark:text-slate-500 font-mono mt-0.5">
            #{session.number} &middot; {session.hash_key.slice(0, 12)}...
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
            <button
              onClick={openPassportUpdate}
              className="btn-secondary text-sm inline-flex items-center gap-1.5"
              title="Talabalar passport seriyasi/raqamini Excel yoki nusxa orqali yangilash"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 9h4M7 13h2m4-1.5a2 2 0 11-4 0 2 2 0 014 0zM13 16.5c0-1.1 1.12-2 2.5-2s2.5.9 2.5 2" />
              </svg>
              Pasport yangilash
            </button>
          </PermissionGate>
          <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
            <button onClick={openEditModal} className="btn-secondary text-sm">
              Tahrirlash
            </button>
          </PermissionGate>
          <PermissionGate permission={PERM.TEST_SESSION_DELETE}>
            <button
              onClick={() => {
                setDeleteError("");
                setShowDeleteConfirm(true);
              }}
              className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 transition"
            >
              O'chirish
            </button>
          </PermissionGate>
        </div>
      </div>

      {/* Stepper */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            Sessiya jarayoni
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${session.is_active ? "bg-emerald-500" : "bg-gray-300 dark:bg-slate-600"}`}
              />
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {session.is_active ? "Faol" : "Nofaol"}
              </span>
            </div>
            <span className="text-xs text-gray-400 dark:text-slate-500">
              Test: {session.test?.name || "—"}
            </span>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center w-full mb-6">
          {sortedStates.map((state, idx) => {
            const isDone = state.key < currentStateKey || (changingState && targetStateId && state.key < (sortedStates.find(s => s.id === targetStateId)?.key ?? 0));
            const isCurrent = state.id === session.test_state_id;
            const isTarget = changingState && state.id === targetStateId;
            const isLoading = isTarget;

            return (
              <div key={state.id} className="flex items-center flex-1 last:flex-none">
                {/* Step circle + label */}
                <div className="flex flex-col items-center relative">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                      isDone
                        ? "bg-primary-600 border-primary-600 text-white"
                        : isCurrent || isTarget
                          ? "bg-white dark:bg-slate-800 border-primary-600 text-primary-600 dark:text-primary-400 shadow-lg shadow-primary-200 dark:shadow-primary-900/30"
                          : "bg-gray-100 dark:bg-slate-700 border-gray-300 dark:border-slate-600 text-gray-400 dark:text-slate-500"
                    }`}
                  >
                    {isDone ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : isLoading ? (
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : (
                      <span className="text-sm font-bold">{idx + 1}</span>
                    )}
                  </div>
                  <span
                    className={`mt-2 text-xs font-medium whitespace-nowrap ${
                      isDone
                        ? "text-primary-600 dark:text-primary-400"
                        : isCurrent || isTarget
                          ? "text-gray-900 dark:text-white"
                          : "text-gray-400 dark:text-slate-500"
                    }`}
                  >
                    {state.name}
                  </span>
                </div>
                {/* Connector line */}
                {idx < sortedStates.length - 1 && (
                  <div className="flex-1 mx-3 mt-[-1.25rem]">
                    <div className="h-1 rounded-full bg-gray-200 dark:bg-slate-700 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary-600 transition-all duration-500 ease-out"
                        style={{
                          width: (() => {
                            const targetKey = sortedStates.find(s => s.id === targetStateId)?.key ?? 0;
                            if (changingState && targetStateId) {
                              // Target step'ga olib keluvchi connector — loadProgress ni
                              // ko'rsatadi (DB state allaqachon target ga o'tib bo'lgan, lekin
                              // ish hali davom etayotgan holatda ham). Boshqa connectorlar:
                              // ungacha bo'lgani — 100%, undan keyingisi — 0%.
                              if (state.key === targetKey - 1) return `${loadProgress}%`;
                              if (state.key < targetKey - 1) return "100%";
                              return "0%";
                            }
                            return state.key < currentStateKey ? "100%" : "0%";
                          })(),
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Progress bar detail (visible during loading) */}
        {changingState && loadProgress > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-600 dark:text-slate-400">
                {progressLabel || "Jarayon davom etmoqda..."}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-primary-600 dark:text-primary-400">
                  {Math.round(loadProgress)}%
                </span>
                {/* Bekor qilish — faqat student yuklash (state key=2) jarayonida */}
                {states.find((s) => s.id === targetStateId)?.key === 2 && (
                  <button
                    type="button"
                    onClick={handleCancelLoad}
                    disabled={cancellingLoad}
                    className="text-xs font-medium px-2.5 py-1 rounded-lg border border-red-200 dark:border-red-800/40 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {cancellingLoad ? "Bekor qilinmoqda..." : "Bekor qilish"}
                  </button>
                )}
              </div>
            </div>
            <div className="w-full h-2.5 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-300 ease-out"
                style={{ width: `${loadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Info notice (masalan, yuklash bekor qilindi) */}
        {stateNotice && (
          <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 rounded-xl flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mt-0.5">
              <svg className="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 text-sm text-amber-700 dark:text-amber-300">{stateNotice}</div>
            <button
              type="button"
              onClick={() => setStateNotice("")}
              className="flex-shrink-0 text-amber-400 hover:text-amber-600 dark:hover:text-amber-300"
              aria-label="Yopish"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Error message */}
        {stateError && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-xl flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center mt-0.5">
              <svg className="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-red-800 dark:text-red-300">
                Holatni o'zgartirishda xatolik
              </p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">{stateError}</p>
              <p className="text-xs text-red-500/70 dark:text-red-400/60 mt-2">
                Sessiya oldingi holatida qoldi. Qayta urinib ko'ring yoki administratorga murojaat qiling.
              </p>
              {/* Resumable qayta yuklash — faqat 'talabalar yuklash' bosqichida (key=2) */}
              {currentStateKey === 2 && !changingState && (
                <button
                  onClick={handleReloadLoad}
                  className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Qolgan kunlarni qayta yuklash
                </button>
              )}
            </div>
            <button
              onClick={() => setStateError("")}
              className="flex-shrink-0 text-red-400 hover:text-red-600 dark:text-red-500 dark:hover:text-red-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* DB'ga insert bo'lmagan talabgorlar (imie + xato sababi) — alert */}
        {failedInserts.length > 0 && (
          <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 rounded-xl">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                  Bazaga yozilmagan talabgorlar: {failedInserts.length} ta
                  {failedInserts.length >= 500 && " (birinchi 500 tasi)"}
                </p>
              </div>
              <button
                onClick={() => setFailedInserts([])}
                className="flex-shrink-0 text-amber-400 hover:text-amber-600 dark:text-amber-500 dark:hover:text-amber-300 transition-colors"
                aria-label="Yopish"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="max-h-60 overflow-y-auto rounded-lg border border-amber-200/60 dark:border-amber-800/30 divide-y divide-amber-100 dark:divide-amber-900/30 bg-white/70 dark:bg-slate-900/40">
              {failedInserts.map((f, i) => (
                <div key={i} className="flex items-start gap-3 px-3 py-1.5 text-xs">
                  <span className="font-mono font-semibold text-gray-700 dark:text-slate-200 whitespace-nowrap shrink-0">
                    {f.imie}
                  </span>
                  <span className="text-amber-700/90 dark:text-amber-300/80 break-words" title={f.reason}>
                    {f.reason}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* O'tkazib yuborilgan talabgorlar (parsing/smena/dublikat) — imie + sabab */}
        {skippedStudents.length > 0 && (
          <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-xl">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-slate-500 dark:text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  O'tkazib yuborilgan talabgorlar: {skippedStudents.length} ta
                  {skippedStudents.length >= 500 && " (birinchi 500 tasi)"}
                </p>
              </div>
              <button
                onClick={() => setSkippedStudents([])}
                className="flex-shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                aria-label="Yopish"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="max-h-60 overflow-y-auto rounded-lg border border-slate-200/70 dark:border-slate-700/50 divide-y divide-slate-100 dark:divide-slate-700/40 bg-white/70 dark:bg-slate-900/40">
              {skippedStudents.map((s, i) => (
                <div key={i} className="flex items-start gap-3 px-3 py-1.5 text-xs">
                  <span className="font-mono font-semibold text-gray-700 dark:text-slate-200 whitespace-nowrap shrink-0">
                    {s.imie}
                  </span>
                  <span className="text-slate-600 dark:text-slate-400 break-words" title={s.reason}>
                    {s.reason}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step buttons */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Hozirgi holat:{" "}
            <span className="font-semibold text-gray-600 dark:text-slate-300">
              {sortedStates.find((s) => s.id === session.test_state_id)?.name || "—"}
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {/* Faqat state 5 dan state 4 ga qaytish tugmasi */}
            {currentStateKey === 5 && (
              <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
                <button
                  onClick={handlePrevStep}
                  disabled={changingState}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Faollashtirish
                </button>
              </PermissionGate>
            )}
            {/* Excel orqali yuklash — faqat state=1 (Yaratilgan) holat uchun */}
            {currentStateKey === 1 && session.smenas.length > 0 && (
              <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
                <button
                  onClick={openExcelUpload}
                  disabled={changingState}
                  title="Studentlar ro'yxatini Excel fayldan yuklash (tashqi API o'rniga)"
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/30 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 border border-emerald-200/70 dark:border-emerald-800/40 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Excel-dan yuklash
                </button>
              </PermissionGate>
            )}
            {/* Keyingi holatga o'tish tugmasi */}
            {currentStepIndex < sortedStates.length - 1 && (
              <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
                <button
                  onClick={handleNextStep}
                  disabled={changingState}
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                >
                  {changingState ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Jarayon davom etmoqda...
                    </>
                  ) : (
                    <>
                      Keyingi: {sortedStates[currentStepIndex + 1]?.name}
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </>
                  )}
                </button>
              </PermissionGate>
            )}
            {currentStepIndex === sortedStates.length - 1 && (
              <span className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Barcha bosqichlar yakunlandi
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Detail info */}
      <div className="glass-card overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            Asosiy ma'lumotlar
          </h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-gray-100 dark:divide-slate-700">
          <InfoBlock label="Boshlanish sanasi" value={formatDate(session.start_date)} />
          <InfoBlock label="Tugash sanasi" value={formatDate(session.finish_date)} />
          <InfoBlock
            label="Kuniga smenalar"
            value={String(session.count_sm_per_day)}
          />
          <InfoBlock
            label="Jami talabalar"
            value={String(session.count_total_student)}
          />
        </div>
        <div className="px-6 py-3 bg-gray-50 dark:bg-slate-800/50 border-t border-gray-100 dark:border-slate-700">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Yaratilgan: {formatDateTime(session.created_at)}
          </p>
        </div>
      </div>

      {/* Student Stats Panel — state >= 3 da ko'rsatiladi */}
      {studentStats && studentStats.not_ready > 0 && (
        <div className="glass-card p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">
              Talabalar holati
            </h3>
            <div className="flex items-center gap-2">
              {!changingState && studentStats.not_ready > 0 && (
                <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
                  <button
                    onClick={handleRetryEmbedding}
                    disabled={retryingEmbedding}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition disabled:opacity-50"
                  >
                    {retryingEmbedding ? "Boshlanmoqda..." : "Qayta embedding"}
                  </button>
                </PermissionGate>
              )}
              <button
                onClick={() => {
                  if (!showFailedStudents && session) {
                    fetchFailedStudents(session);
                  }
                  setShowFailedStudents(!showFailedStudents);
                }}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
              >
                {showFailedStudents ? "Yopish" : "Batafsil"}
              </button>
            </div>
          </div>

          {/* Stats summary */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
            <div className="bg-gray-50 dark:bg-slate-800 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-gray-800 dark:text-slate-200">{studentStats.total}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">Jami</p>
            </div>
            <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{studentStats.ready}</p>
              <p className="text-xs text-emerald-600/70 dark:text-emerald-400/70">Tayyor</p>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-red-600 dark:text-red-400">{studentStats.not_ready}</p>
              <p className="text-xs text-red-600/70 dark:text-red-400/70">Tayyor emas</p>
            </div>
            <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-orange-600 dark:text-orange-400">{studentStats.no_image}</p>
              <p className="text-xs text-orange-600/70 dark:text-orange-400/70">Rasmsiz</p>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-purple-600 dark:text-purple-400">{studentStats.no_face}</p>
              <p className="text-xs text-purple-600/70 dark:text-purple-400/70">Yuzsiz</p>
            </div>
          </div>

          {/* Tayyor emas bo'lgan studentlar ro'yxati */}
          {showFailedStudents && (
            <div className="border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden">
              {loadingFailedStudents ? (
                <div className="text-center py-6 text-gray-400 text-sm">Yuklanmoqda...</div>
              ) : failedStudents.length === 0 ? (
                <div className="text-center py-6 text-gray-400 text-sm">Tayyor bo'lmagan talabalar topilmadi</div>
              ) : (
                <div className="overflow-x-auto max-h-80 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0">
                      <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                        <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-slate-400">ID</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-slate-400">F.I.O</th>
                        <th className="px-3 py-2 text-center font-medium text-gray-500 dark:text-slate-400">Rasm</th>
                        <th className="px-3 py-2 text-center font-medium text-gray-500 dark:text-slate-400">Yuz</th>
                        <th className="px-3 py-2 text-center font-medium text-gray-500 dark:text-slate-400">Amal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {failedStudents.map((st) => (
                        <tr key={st.id} className="border-b border-gray-100 dark:border-slate-700/50">
                          <td className="px-3 py-2 text-gray-500 dark:text-slate-400 font-mono text-xs">{st.id}</td>
                          <td className="px-3 py-2 font-medium text-gray-800 dark:text-slate-200">
                            {st.last_name} {st.first_name} {st.middle_name || ""}
                          </td>
                          <td className="px-3 py-2 text-center">
                            <span className={`inline-block w-2.5 h-2.5 rounded-full ${st.is_image ? "bg-emerald-500" : "bg-red-400"}`} />
                          </td>
                          <td className="px-3 py-2 text-center">
                            <span className={`inline-block w-2.5 h-2.5 rounded-full ${st.is_face ? "bg-emerald-500" : "bg-red-400"}`} />
                          </td>
                          <td className="px-3 py-2 text-center">
                            {!st.is_image ? (
                              <label className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 rounded-lg cursor-pointer hover:bg-primary-100 dark:hover:bg-primary-900/30 transition">
                                {uploadingImageId === st.id ? (
                                  "Yuklanmoqda..."
                                ) : (
                                  <>
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    Rasm yuklash
                                  </>
                                )}
                                <input
                                  type="file"
                                  accept="image/*"
                                  className="hidden"
                                  disabled={uploadingImageId === st.id}
                                  onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleUploadImage(st.id, file);
                                    e.target.value = "";
                                  }}
                                />
                              </label>
                            ) : !st.is_face ? (
                              <span className="text-xs text-gray-400 dark:text-slate-500">Yuz aniqlanmadi</span>
                            ) : null}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Smenas table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            Smenalar ({session.smenas.length})
          </h3>
          <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
            <button
              onClick={openAddSmena}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
            >
              + Smena qo'shish
            </button>
          </PermissionGate>
        </div>
        {session.smenas.length === 0 ? (
          <div className="text-center py-10 text-gray-400 dark:text-slate-500 text-sm">
            Smenalar qo'shilmagan
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-slate-400">
                    #
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-slate-400">
                    Smena
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-slate-400">
                    Kun
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500 dark:text-slate-400">
                    Faol
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500 dark:text-slate-400">
                    Amallar
                  </th>
                </tr>
              </thead>
              <tbody>
                {session.smenas.map((sm, idx) => (
                  <tr
                    key={sm.id}
                    className="border-b border-gray-100 dark:border-slate-700/50"
                  >
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                      {idx + 1}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">
                      {sm.smena?.name || `Smena #${sm.test_smena_id}`}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                      {formatDate(sm.day)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full ${sm.is_active ? "bg-emerald-500" : "bg-red-400"}`}
                      />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <PermissionGate permission={PERM.TEST_SESSION_UPDATE}>
                        <button
                          onClick={() =>
                            setRemoveSmenaTarget({
                              id: sm.id,
                              name: sm.smena?.name || `#${sm.id}`,
                            })
                          }
                          className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium"
                        >
                          O'chirish
                        </button>
                      </PermissionGate>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ========== MODALS ========== */}

      {/* Edit Modal */}
      {showEdit && (
        <Modal
          title="Sessiyani tahrirlash"
          onClose={() => setShowEdit(false)}
        >
          <div className="space-y-4">
            {editError && <ErrorBox message={editError} />}
            <Field label="Sessiya nomi">
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="input-field"
              />
            </Field>
            <Field label="Test">
              <Md3Select
                value={editTestId ? String(editTestId) : ""}
                onChange={(v) => setEditTestId(Number(v))}
                options={tests.map((t) => ({
                  value: String(t.id),
                  label: t.name,
                }))}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Boshlanish sanasi">
                <input
                  type="date"
                  value={editStartDate}
                  onChange={(e) => setEditStartDate(e.target.value)}
                  className="input-field"
                />
              </Field>
              <Field label="Tugash sanasi">
                <input
                  type="date"
                  value={editFinishDate}
                  onChange={(e) => setEditFinishDate(e.target.value)}
                  className="input-field"
                />
              </Field>
            </div>
            <Field label="Kuniga smenalar soni">
              <input
                type="number"
                min={0}
                value={editSmPerDay}
                onChange={(e) => setEditSmPerDay(Number(e.target.value))}
                className="input-field"
              />
            </Field>
            <Field label="Faollik">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={editIsActive}
                  onChange={(e) => setEditIsActive(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-slate-300">
                  Faol
                </span>
              </label>
            </Field>
          </div>
          <ModalFooter
            onCancel={() => setShowEdit(false)}
            onConfirm={handleEdit}
            confirmText={editSubmitting ? "Saqlanmoqda..." : "Saqlash"}
            disabled={editSubmitting}
          />
        </Modal>
      )}

      {/* Delete Confirm Modal */}
      {showDeleteConfirm && (
        <Modal
          title="Sessiyani o'chirish"
          onClose={() => setShowDeleteConfirm(false)}
        >
          <div className="py-2">
            {deleteError && <ErrorBox message={deleteError} />}
            <p className="text-sm text-gray-600 dark:text-slate-400">
              <strong className="text-gray-800 dark:text-slate-200">
                "{session.name}"
              </strong>{" "}
              sessiyasini o'chirishni tasdiqlaysizmi? Bu amalni qaytarib
              bo'lmaydi.
            </p>
          </div>
          <ModalFooter
            onCancel={() => setShowDeleteConfirm(false)}
            onConfirm={handleDelete}
            confirmText={deleting ? "O'chirilmoqda..." : "Ha, o'chirish"}
            disabled={deleting}
            danger
          />
        </Modal>
      )}

      {/* Add Smena Modal */}
      {showAddSmena && (
        <Modal title="Smena qo'shish" onClose={() => setShowAddSmena(false)}>
          <div className="space-y-4">
            {addSmenaError && <ErrorBox message={addSmenaError} />}
            <Field label="Smena">
              <Md3Select
                value={addSmenaId ? String(addSmenaId) : ""}
                onChange={(v) => setAddSmenaId(Number(v))}
                options={smenas.map((sm) => ({
                  value: String(sm.id),
                  label: sm.name,
                }))}
              />
            </Field>
            <Field label="Kun">
              <input
                type="date"
                value={addSmenaDay}
                onChange={(e) => setAddSmenaDay(e.target.value)}
                className="input-field"
              />
            </Field>
          </div>
          <ModalFooter
            onCancel={() => setShowAddSmena(false)}
            onConfirm={handleAddSmena}
            confirmText={addSmenaSubmitting ? "Qo'shilmoqda..." : "Qo'shish"}
            disabled={addSmenaSubmitting}
          />
        </Modal>
      )}

      {/* Excel Upload Modal — faqat state.key=1 (Yaratilgan) holatda */}
      {showExcelUpload && (
        <Modal
          title="Excel'dan studentlarni yuklash"
          onClose={() => (excelSubmitting ? undefined : setShowExcelUpload(false))}
        >
          <div className="space-y-4">
            {excelError && <ErrorBox message={excelError} />}

            {/* Help / instructions */}
            <div className="p-4 rounded-xl bg-sky-50 dark:bg-sky-900/20 border border-sky-200/60 dark:border-sky-800/40 text-[13px] text-sky-900 dark:text-sky-200 space-y-1.5">
              <p className="font-semibold flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Talab qilinadigan ustunlar
              </p>
              <p className="text-[12px] leading-relaxed">
                <code className="font-mono">last_name</code>, <code className="font-mono">first_name</code>,{" "}
                <code className="font-mono">middle_name</code>, <code className="font-mono">imei</code>,{" "}
                <code className="font-mono">ps_ser</code>, <code className="font-mono">ps_num</code>,{" "}
                <code className="font-mono">region number</code>, <code className="font-mono">zone number</code>,{" "}
                <code className="font-mono">smena number</code>, <code className="font-mono">gr_n</code>,{" "}
                <code className="font-mono">e_date</code>, <code className="font-mono">subject_name</code>
              </p>
              <ul className="text-[12px] list-disc pl-5 space-y-0.5 mt-1">
                <li>Birinchi qator — sarlavha. Keyingilar — qatorlar.</li>
                <li><strong>smena number</strong> bo'yicha sessiyadagi smenaga bog'lanadi (sana = <code className="font-mono">e_date</code>).</li>
                <li>Yuklab olingach FIO va rasm GTSP xizmatidan avtomatik to'ldiriladi.</li>
              </ul>
            </div>

            <button
              type="button"
              onClick={handleDownloadTemplate}
              disabled={templateDownloading || excelSubmitting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-700 dark:text-primary-200 bg-primary-50 dark:bg-primary-900/30 hover:bg-primary-100 dark:hover:bg-primary-900/50 border border-primary-200/70 dark:border-primary-800/40 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
              </svg>
              {templateDownloading ? "Yuklab olinmoqda..." : "Shablonni yuklab olish (.xlsx)"}
            </button>

            <Field label="Excel fayl (.xlsx)">
              <input
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null;
                  setExcelFile(f);
                  setExcelError(null);
                }}
                disabled={excelSubmitting}
                className="block w-full text-sm text-gray-600 dark:text-slate-300
                  file:mr-3 file:py-2.5 file:px-4 file:rounded-full file:border-0
                  file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700
                  dark:file:bg-primary-900/40 dark:file:text-primary-200
                  hover:file:bg-primary-100 dark:hover:file:bg-primary-900/60
                  file:cursor-pointer cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {excelFile && (
                <p className="mt-2 text-[12px] text-gray-500 dark:text-slate-400">
                  Tanlandi: <span className="font-medium text-gray-700 dark:text-slate-300">{excelFile.name}</span>{" "}
                  <span className="text-gray-400 dark:text-slate-500">
                    ({Math.ceil(excelFile.size / 1024)} KB)
                  </span>
                </p>
              )}
            </Field>

            <p className="text-[12px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg flex items-start gap-2">
              <svg className="w-4 h-4 mt-px shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>
                Yuborilgach jarayon arqa fonda davom etadi — modal yopilib,
                progress ko'rsatkichi ostida ko'rasiz. Yakunida sessiya
                <strong> "Yuklab olindi"</strong> holatiga o'tadi.
              </span>
            </p>
          </div>
          <ModalFooter
            onCancel={() => setShowExcelUpload(false)}
            onConfirm={handleExcelUpload}
            confirmText={excelSubmitting ? "Yuborilmoqda..." : "Yuborish va boshlash"}
            disabled={!excelFile || excelSubmitting}
          />
        </Modal>
      )}

      {/* Passport (ps_ser/ps_num) ommaviy yangilash modali */}
      {showPassportUpdate && (() => {
        const parsed =
          passportMode === "paste" ? parsePastedPassports(passportPaste) : [];
        const invalidCount = parsed.filter(
          (r) => validatePassportRowClient(r) !== null,
        ).length;
        const canSubmit =
          !passportSubmitting &&
          (passportMode === "excel"
            ? !!passportFile
            : parsed.length > 0 && invalidCount < parsed.length);

        return (
          <Modal
            title="Pasport ma'lumotlarini yangilash"
            onClose={() =>
              passportSubmitting ? undefined : setShowPassportUpdate(false)
            }
          >
            <div className="space-y-4">
              {passportError && <ErrorBox message={passportError} />}

              {/* Natija ko'rsatkichi */}
              {passportResult ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <ResultStat
                      value={passportResult.updated}
                      label="Yangilandi"
                      tone="emerald"
                    />
                    <ResultStat
                      value={passportResult.not_found.length}
                      label="Topilmadi"
                      tone="amber"
                    />
                    <ResultStat
                      value={passportResult.invalid.length}
                      label="Xato qator"
                      tone="rose"
                    />
                  </div>

                  {passportResult.not_found.length > 0 && (
                    <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200/60 dark:border-amber-800/40">
                      <p className="text-[12px] font-semibold text-amber-800 dark:text-amber-200 mb-1">
                        Sessiyada topilmagan JSHSHIR'lar ({passportResult.not_found.length})
                      </p>
                      <p className="text-[12px] font-mono text-amber-700 dark:text-amber-300 max-h-24 overflow-y-auto break-all">
                        {passportResult.not_found.join(", ")}
                      </p>
                    </div>
                  )}

                  {passportResult.invalid.length > 0 && (
                    <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200/60 dark:border-rose-800/40 max-h-32 overflow-y-auto">
                      <p className="text-[12px] font-semibold text-rose-800 dark:text-rose-200 mb-1">
                        Xato qatorlar ({passportResult.invalid.length})
                      </p>
                      <ul className="text-[12px] text-rose-700 dark:text-rose-300 space-y-0.5">
                        {passportResult.invalid.slice(0, 50).map((it) => (
                          <li key={it.row}>
                            <span className="font-mono">#{it.row}</span>{" "}
                            {it.jshshir && <span className="font-mono">{it.jshshir}</span>} — {it.error}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="flex justify-end gap-3 mt-2">
                    <button
                      onClick={() => {
                        setPassportResult(null);
                        setPassportPaste("");
                        setPassportFile(null);
                      }}
                      className="btn-secondary"
                    >
                      Yana yangilash
                    </button>
                    <button
                      onClick={() => setShowPassportUpdate(false)}
                      className="btn-primary"
                    >
                      Yopish
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Rejim tablari */}
                  <div className="flex p-1 gap-1 rounded-xl bg-gray-100 dark:bg-slate-700/40">
                    {([
                      ["paste", "Nusxa joylash"],
                      ["excel", "Excel fayl"],
                    ] as const).map(([key, label]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => {
                          setPassportMode(key);
                          setPassportError(null);
                        }}
                        disabled={passportSubmitting}
                        className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                          passportMode === key
                            ? "bg-white dark:bg-slate-800 text-primary-700 dark:text-primary-200 shadow-sm"
                            : "text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* Yo'riqnoma */}
                  <div className="p-4 rounded-xl bg-sky-50 dark:bg-sky-900/20 border border-sky-200/60 dark:border-sky-800/40 text-[13px] text-sky-900 dark:text-sky-200 space-y-1.5">
                    <p className="font-semibold flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Ustunlar: <code className="font-mono">jshshir</code>,{" "}
                      <code className="font-mono">ps_ser</code>,{" "}
                      <code className="font-mono">ps_num</code>
                    </p>
                    <p className="text-[12px] leading-relaxed">
                      <strong>jshshir</strong> bo'yicha shu sessiyadagi talaba topiladi
                      va passport seriyasi/raqami yangilanadi. Topilmagan JSHSHIR'lar
                      o'tkazib yuboriladi.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handlePassportTemplate}
                    disabled={passportTplDownloading || passportSubmitting}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-700 dark:text-primary-200 bg-primary-50 dark:bg-primary-900/30 hover:bg-primary-100 dark:hover:bg-primary-900/50 border border-primary-200/70 dark:border-primary-800/40 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
                    </svg>
                    {passportTplDownloading ? "Yuklab olinmoqda..." : "Shablonni yuklab olish (.xlsx)"}
                  </button>

                  {passportMode === "paste" ? (
                    <div className="space-y-2">
                      <Field label="Excel'dan nusxalab joylashtiring (jshshir, ps_ser, ps_num)">
                        <textarea
                          value={passportPaste}
                          onChange={(e) => {
                            setPassportPaste(e.target.value);
                            setPassportError(null);
                          }}
                          disabled={passportSubmitting}
                          rows={6}
                          placeholder={"32401200012345\tAA\t1234567\n33301200067890\tAB\t7654321"}
                          className="input-field w-full font-mono text-[13px] resize-y"
                        />
                      </Field>

                      {/* Jonli ko'rinish (preview) */}
                      {parsed.length > 0 && (
                        <div className="rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
                          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-slate-700/40 text-[12px]">
                            <span className="font-medium text-gray-600 dark:text-slate-300">
                              {parsed.length} qator aniqlandi
                            </span>
                            {invalidCount > 0 && (
                              <span className="text-rose-600 dark:text-rose-400 font-medium">
                                {invalidCount} ta xato
                              </span>
                            )}
                          </div>
                          <div className="max-h-44 overflow-y-auto">
                            <table className="w-full text-[12px]">
                              <thead className="sticky top-0 bg-white dark:bg-slate-800">
                                <tr className="text-left text-gray-400 dark:text-slate-500">
                                  <th className="px-3 py-1.5 font-medium">#</th>
                                  <th className="px-3 py-1.5 font-medium">jshshir</th>
                                  <th className="px-3 py-1.5 font-medium">ps_ser</th>
                                  <th className="px-3 py-1.5 font-medium">ps_num</th>
                                </tr>
                              </thead>
                              <tbody className="font-mono">
                                {parsed.slice(0, 100).map((r, i) => {
                                  const err = validatePassportRowClient(r);
                                  return (
                                    <tr
                                      key={i}
                                      className={`border-t border-gray-100 dark:border-slate-700/60 ${
                                        err
                                          ? "bg-rose-50/60 dark:bg-rose-900/10"
                                          : ""
                                      }`}
                                      title={err ?? ""}
                                    >
                                      <td className="px-3 py-1 text-gray-400">{i + 1}</td>
                                      <td className="px-3 py-1 text-gray-700 dark:text-slate-200">
                                        {r.jshshir || <span className="text-rose-500">—</span>}
                                      </td>
                                      <td className="px-3 py-1 text-gray-700 dark:text-slate-200">
                                        {r.ps_ser || <span className="text-rose-500">—</span>}
                                      </td>
                                      <td className="px-3 py-1 text-gray-700 dark:text-slate-200">
                                        {r.ps_num || <span className="text-rose-500">—</span>}
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <Field label="Excel fayl (.xlsx)">
                      <input
                        type="file"
                        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        onChange={(e) => {
                          setPassportFile(e.target.files?.[0] ?? null);
                          setPassportError(null);
                        }}
                        disabled={passportSubmitting}
                        className="block w-full text-sm text-gray-600 dark:text-slate-300
                          file:mr-3 file:py-2.5 file:px-4 file:rounded-full file:border-0
                          file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700
                          dark:file:bg-primary-900/40 dark:file:text-primary-200
                          hover:file:bg-primary-100 dark:hover:file:bg-primary-900/60
                          file:cursor-pointer cursor-pointer
                          disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      {passportFile && (
                        <p className="mt-2 text-[12px] text-gray-500 dark:text-slate-400">
                          Tanlandi:{" "}
                          <span className="font-medium text-gray-700 dark:text-slate-300">
                            {passportFile.name}
                          </span>{" "}
                          <span className="text-gray-400 dark:text-slate-500">
                            ({Math.ceil(passportFile.size / 1024)} KB)
                          </span>
                        </p>
                      )}
                    </Field>
                  )}
                </>
              )}
            </div>

            {!passportResult && (
              <ModalFooter
                onCancel={() => setShowPassportUpdate(false)}
                onConfirm={handlePassportSubmit}
                confirmText={passportSubmitting ? "Yangilanmoqda..." : "Yangilash"}
                disabled={!canSubmit}
              />
            )}
          </Modal>
        );
      })()}

      {/* Remove Smena Confirm */}
      {removeSmenaTarget && (() => {
        const isLastSmena = session.smenas.length === 1;
        const willResetState = isLastSmena && currentStateKey > 1;
        const isActiveSession = isLastSmena && currentStateKey === 4;
        return (
          <Modal
            title="Smenani o'chirish"
            onClose={() => setRemoveSmenaTarget(null)}
          >
            <div className="py-2 space-y-3">
              <p className="text-sm text-gray-600 dark:text-slate-400">
                <strong className="text-gray-800 dark:text-slate-200">
                  "{removeSmenaTarget.name}"
                </strong>{" "}
                smenasini sessiyadan olib tashlashni tasdiqlaysizmi?
              </p>

              {/* Faol imtihon — eng kuchli ogohlantirish */}
              {isActiveSession && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-800/60 text-[13px] text-red-900 dark:text-red-200 space-y-1.5">
                  <p className="font-bold flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    DIQQAT! Faol imtihon sessiyasi
                  </p>
                  <p>
                    Bu sessiya hozir <strong>faol holatda</strong> (imtihon davom etmoqda).
                    Oxirgi smenani o'chirish quyidagilarga olib keladi:
                  </p>
                  <ul className="list-disc pl-5 space-y-0.5">
                    <li>Barcha {session.count_total_student.toLocaleString()} ta talaba o'chiriladi</li>
                    <li>Sessiya <strong>"Yaratilgan"</strong> holatiga qaytariladi</li>
                    <li>Davomat ma'lumotlari yo'qoladi</li>
                  </ul>
                  <p className="font-semibold mt-1">
                    Imtihon paytida bu harakatni faqat zarurat bo'lganda bajaring!
                  </p>
                </div>
              )}

              {/* Faol bo'lmagan, lekin oxirgi smena — o'rta darajadagi ogohlantirish */}
              {willResetState && !isActiveSession && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 text-[13px] text-amber-900 dark:text-amber-200 space-y-1.5">
                  <p className="font-semibold flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Bu oxirgi smena
                  </p>
                  <p>
                    O'chirgandan keyin sessiyada hech qanday smena qolmaydi va sessiya
                    avtomatik <strong>"Yaratilgan"</strong> holatiga qaytariladi.
                  </p>
                  {session.count_total_student > 0 && (
                    <p>
                      Bundan tashqari <strong>{session.count_total_student.toLocaleString()} ta talaba</strong>{" "}
                      ma'lumotlari ham o'chiriladi.
                    </p>
                  )}
                </div>
              )}
            </div>
            <ModalFooter
              onCancel={() => setRemoveSmenaTarget(null)}
              onConfirm={handleRemoveSmena}
              confirmText={
                removingSmena
                  ? "O'chirilmoqda..."
                  : isActiveSession
                    ? "Ha, baribir o'chirish"
                    : "Ha, o'chirish"
              }
              disabled={removingSmena}
              danger
            />
          </Modal>
        );
      })()}
    </div>
  );
}

/* ---- Reusable small components ---- */

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-6 py-4">
      <p className="label-text mb-1">{label}</p>
      <p className="text-sm font-semibold text-gray-800 dark:text-slate-200">
        {value}
      </p>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg">
      {message}
    </div>
  );
}

// Passport yangilash natijasi uchun statistika katakchasi
function ResultStat({
  value,
  label,
  tone,
}: {
  value: number;
  label: string;
  tone: "emerald" | "amber" | "rose";
}) {
  const tones = {
    emerald: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border-emerald-200/60 dark:border-emerald-800/40",
    amber: "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border-amber-200/60 dark:border-amber-800/40",
    rose: "bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 border-rose-200/60 dark:border-rose-800/40",
  } as const;
  return (
    <div className={`flex flex-col items-center justify-center py-3 rounded-xl border ${tones[tone]}`}>
      <span className="text-2xl font-bold tabular-nums">{value}</span>
      <span className="text-[12px] font-medium mt-0.5">{label}</span>
    </div>
  );
}

/**
 * Excel'dan nusxalab joylashtirilgan matnni `{jshshir, ps_ser, ps_num}`
 * qatorlariga ajratadi. Ustunlar tab (Excel paste), ; , yoki 2+ bo'shliq
 * bilan ajratilishi mumkin. Sarlavha qatori (jshshir/ps_ser/...) o'tkaziladi.
 */
function parsePastedPassports(text: string): PassportUpdateRow[] {
  const rows: PassportUpdateRow[] = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    if (/jshshir|ps_?ser|ps_?num|seriya|raqam/i.test(line)) continue; // sarlavha
    const cols = line.split(/\t|;|,|\s{2,}/).map((c) => c.trim());
    const jshshir = cols[0] ?? "";
    let ps_ser = (cols[1] ?? "").toUpperCase();
    let ps_num = cols[2] ?? "";
    // Seriya+raqam bitta ustunda birlashib kelgan bo'lsa — ajratamiz.
    [ps_ser, ps_num] = splitCombinedPassport(ps_ser, ps_num);
    if (!jshshir && !ps_ser && !ps_num) continue;
    rows.push({ jshshir, ps_ser, ps_num });
  }
  return rows;
}

// "AA1234567" / "AA 1234567" / "AA-1234567" -> ["AA", "1234567"].
// ps_num to'lgan bo'lsa yoki naqshga mos kelmasa — o'zgarishsiz qaytaradi.
const COMBINED_PASSPORT_RE = /^([A-Za-z]{1,5})[\s-]*(\d{1,10})$/;
function splitCombinedPassport(ps_ser: string, ps_num: string): [string, string] {
  if (ps_num || !ps_ser) return [ps_ser, ps_num];
  const m = COMBINED_PASSPORT_RE.exec(ps_ser.trim());
  if (!m) return [ps_ser, ps_num];
  return [m[1].toUpperCase(), m[2]];
}

/** Bitta qatorni client tomonda tekshiradi (backend bilan bir xil qoidalar). */
function validatePassportRowClient(r: PassportUpdateRow): string | null {
  if (!r.jshshir) return "JSHSHIR bo'sh";
  if (!/^\d{1,14}$/.test(r.jshshir)) return "JSHSHIR 14 ta raqamgacha bo'lishi kerak";
  if (!r.ps_ser) return "Seriya bo'sh";
  if (r.ps_ser.length > 5) return "Seriya 5 belgidan oshmasin";
  if (!r.ps_num) return "Raqam bo'sh";
  if (r.ps_num.length > 10) return "Raqam 10 belgidan oshmasin";
  return null;
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function ModalFooter({
  onCancel,
  onConfirm,
  confirmText,
  disabled,
  danger,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  confirmText: string;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <div className="flex justify-end gap-3 mt-6">
      <button onClick={onCancel} className="btn-secondary" disabled={disabled}>
        Bekor qilish
      </button>
      <button
        onClick={onConfirm}
        disabled={disabled}
        className={
          danger
            ? "px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition disabled:opacity-50"
            : "btn-primary"
        }
      >
        {confirmText}
      </button>
    </div>
  );
}
