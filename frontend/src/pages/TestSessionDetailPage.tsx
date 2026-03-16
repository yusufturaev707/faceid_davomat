import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type {
  SessionStateResponse,
  SmenaResponse,
  TestResponse,
  TestSessionResponse,
} from "../interfaces";
import {
  addSmenaToSessionApi,
  changeSessionStateApi,
  deleteTestSessionApi,
  getSessionStatesLookupApi,
  getSmenasLookupApi,
  getTestSessionApi,
  getTestsLookupApi,
  removeSmenaFromSessionApi,
  updateTestSessionApi,
} from "../api";
import PageLoader from "../components/PageLoader";
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
  const [loadProgress, setLoadProgress] = useState(0);

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

  const [stateError, setStateError] = useState("");

  // Sorted states by key for stepper
  const sortedStates = [...states].sort((a, b) => a.key - b.key);
  const currentStateKey = sortedStates.find(
    (s) => s.id === session?.test_state_id
  )?.key ?? 0;
  const currentStepIndex = sortedStates.findIndex(
    (s) => s.id === session?.test_state_id
  );

  const handleNextStep = async () => {
    if (!session || currentStepIndex < 0) return;
    const nextState = sortedStates[currentStepIndex + 1];
    if (!nextState) return;

    setChangingState(true);
    setStateError("");
    setLoadProgress(0);

    // Simulate progress for loading state (key=2)
    let progressInterval: ReturnType<typeof setInterval> | null = null;
    if (nextState.key === 2) {
      progressInterval = setInterval(() => {
        setLoadProgress((prev) => {
          if (prev >= 92) return prev;
          return prev + Math.random() * 8 + 2;
        });
      }, 400);
    }

    try {
      const updated = await changeSessionStateApi(session.id, nextState.id);
      if (progressInterval) {
        clearInterval(progressInterval);
        setLoadProgress(100);
      }
      // Small delay to show 100% before transitioning
      await new Promise((r) => setTimeout(r, 500));
      setSession(updated);
      setLoadProgress(0);
    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      setLoadProgress(0);
      setStateError(extractErrorMessage(err));
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
          <button onClick={openEditModal} className="btn-secondary text-sm">
            Tahrirlash
          </button>
          <button
            onClick={() => {
              setDeleteError("");
              setShowDeleteConfirm(true);
            }}
            className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 transition"
          >
            O'chirish
          </button>
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
            const isDone = state.key < currentStateKey;
            const isCurrent = state.id === session.test_state_id;
            const isLoading = isCurrent && changingState;

            return (
              <div key={state.id} className="flex items-center flex-1 last:flex-none">
                {/* Step circle + label */}
                <div className="flex flex-col items-center relative">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                      isDone
                        ? "bg-primary-600 border-primary-600 text-white"
                        : isCurrent
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
                        : isCurrent
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
                          width:
                            state.key < currentStateKey
                              ? "100%"
                              : state.id === session.test_state_id && changingState
                                ? `${loadProgress}%`
                                : "0%",
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
                Talabalar yuklanmoqda...
              </span>
              <span className="text-xs font-bold text-primary-600 dark:text-primary-400">
                {Math.round(loadProgress)}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-300 ease-out"
                style={{ width: `${loadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {stateError && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <p className="text-xs text-red-600 dark:text-red-400">{stateError}</p>
          </div>
        )}

        {/* Next step button */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Hozirgi holat:{" "}
            <span className="font-semibold text-gray-600 dark:text-slate-300">
              {sortedStates.find((s) => s.id === session.test_state_id)?.name || "—"}
            </span>
          </p>
          {currentStepIndex < sortedStates.length - 1 && (
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

      {/* Smenas table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            Smenalar ({session.smenas.length})
          </h3>
          <button
            onClick={openAddSmena}
            className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
          >
            + Smena qo'shish
          </button>
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
              <select
                value={editTestId}
                onChange={(e) => setEditTestId(Number(e.target.value))}
                className="input-field"
              >
                {tests.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
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
              <select
                value={addSmenaId}
                onChange={(e) => setAddSmenaId(Number(e.target.value))}
                className="input-field"
              >
                {smenas.map((sm) => (
                  <option key={sm.id} value={sm.id}>
                    {sm.name}
                  </option>
                ))}
              </select>
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

      {/* Remove Smena Confirm */}
      {removeSmenaTarget && (
        <Modal
          title="Smenani o'chirish"
          onClose={() => setRemoveSmenaTarget(null)}
        >
          <div className="py-2">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              <strong className="text-gray-800 dark:text-slate-200">
                "{removeSmenaTarget.name}"
              </strong>{" "}
              smenasini sessiyadan olib tashlashni tasdiqlaysizmi?
            </p>
          </div>
          <ModalFooter
            onCancel={() => setRemoveSmenaTarget(null)}
            onConfirm={handleRemoveSmena}
            confirmText={removingSmena ? "O'chirilmoqda..." : "Ha, o'chirish"}
            disabled={removingSmena}
            danger
          />
        </Modal>
      )}
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
