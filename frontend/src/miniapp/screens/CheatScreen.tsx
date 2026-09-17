/**
 * Chetlatish: JShShIR → (bir nechta bo'lsa tanlash) → tur → sabab → tasdiqlash.
 * Qidiruv butun test tadbiri bo'yicha (smena bilan cheklanmaydi), allaqachon
 * chetlatilganlar chiqmaydi. Backend idempotent: takroriy so'rov `already_cheating`.
 */

import { useState } from "react";
import { api } from "../api";
import { Ban } from "../components/icons";
import { JshshirSearch } from "../components/JshshirSearch";
import { StudentSlotPicker, StudentSlotSection } from "../components/StudentSlot";
import {
  Button,
  DetailRow,
  ErrorState,
  LoadingState,
  MainButton,
  Notice,
  Row,
  Screen,
  Section,
  useToast,
} from "../components/ui";
import { useApp } from "../context";
import { useAsync } from "../hooks";
import { useBackHandler } from "../navigation";
import { telegram } from "../telegram";
import type {
  CheatResponse,
  ReadySession,
  Reason,
  ReasonType,
  SmenaInfo,
  StudentSlot,
} from "../types";
import { formatDay } from "../utils/format";

type State =
  | { step: "search"; notice?: { tone: "warning" | "accent"; text: string } }
  | { step: "pick"; matches: StudentSlot[] }
  | { step: "type"; slot: StudentSlot; matches: StudentSlot[] }
  | { step: "reason"; slot: StudentSlot; matches: StudentSlot[]; type: ReasonType }
  | { step: "confirm"; slot: StudentSlot; matches: StudentSlot[]; type: ReasonType; reason: Reason }
  | { step: "done"; slot: StudentSlot; result: CheatResponse };

export function CheatScreen({ session, smena }: { session: ReadySession; smena: SmenaInfo }) {
  const { region } = useApp();
  const toast = useToast();
  const [state, setState] = useState<State>({ step: "search" });
  const [jshshir, setJshshir] = useState("");
  const [busy, setBusy] = useState(false);

  useBackHandler(() => {
    if (busy) return true;
    switch (state.step) {
      case "confirm":
        setState({ step: "reason", slot: state.slot, matches: state.matches, type: state.type });
        return true;
      case "reason":
        setState({ step: "type", slot: state.slot, matches: state.matches });
        return true;
      case "type":
        setState(state.matches.length > 1 ? { step: "pick", matches: state.matches } : { step: "search" });
        return true;
      case "pick":
        setState({ step: "search" });
        return true;
      default:
        return false;
    }
  });

  const search = async (value: string) => {
    setJshshir(value);
    setBusy(true);
    try {
      const response = await api.findForCheat(session.id, region.id, value);
      if (response.status === "already_cheating") {
        telegram.haptic("warning");
        setState({ step: "search", notice: { tone: "accent", text: response.message } });
      } else if (response.status !== "ok" || response.matches.length === 0) {
        telegram.haptic("warning");
        setState({
          step: "search",
          notice: { tone: "warning", text: response.message || "Talabgor topilmadi." },
        });
      } else if (response.matches.length === 1) {
        setState({ step: "type", slot: response.matches[0], matches: response.matches });
      } else {
        setState({ step: "pick", matches: response.matches });
      }
    } catch (err) {
      telegram.haptic("error");
      toast((err as Error).message, "destructive");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (slot: StudentSlot, reason: Reason) => {
    setBusy(true);
    try {
      const result = await api.cheat(slot.student_id, session.id, region.id, reason.id);
      telegram.haptic(result.status === "ok" ? "success" : "warning");
      setState({ step: "done", slot, result });
    } catch (err) {
      telegram.haptic("error");
      toast((err as Error).message, "destructive");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="Chetlatish" subtitle={`${session.name} • ${formatDay(smena.day)}`}>
      {state.step === "search" && (
        <>
          {state.notice && (
            <Notice tone={state.notice.tone} title={state.notice.tone === "accent" ? "Allaqachon chetlatilgan" : "Topilmadi"}>
              {state.notice.text}
            </Notice>
          )}
          <JshshirSearch
            key={state.notice?.text ?? "search"}
            initial={jshshir}
            loading={busy}
            footer="Talabgor butun test tadbiri bo'yicha qidiriladi."
            onSearch={search}
          />
        </>
      )}

      {state.step === "pick" && (
        <StudentSlotPicker
          slots={state.matches}
          onPick={(slot) => setState({ step: "type", slot, matches: state.matches })}
        />
      )}

      {state.step === "type" && (
        <>
          <StudentSlotSection slot={state.slot} title="Talabgor" />
          <ReasonTypePicker
            onPick={(type) => setState({ step: "reason", slot: state.slot, matches: state.matches, type })}
          />
        </>
      )}

      {state.step === "reason" && (
        <ReasonPicker
          type={state.type}
          onPick={(reason) =>
            setState({ step: "confirm", slot: state.slot, matches: state.matches, type: state.type, reason })
          }
        />
      )}

      {state.step === "confirm" && (
        <>
          <Notice tone="destructive" title="Chetlatishni tasdiqlang">
            Talabgor chetlatiladi va qora ro'yxatga kiritiladi. Bu amalni ilovadan bekor qilib bo'lmaydi.
          </Notice>
          <Section title="Chetlatish">
            <DetailRow label="Tur" value={state.type.name} />
            <DetailRow label="Sabab" value={state.reason.name} />
          </Section>
          <StudentSlotSection slot={state.slot} title="Talabgor" />
          <Button variant="plain" onClick={() => setState({ step: "search" })} disabled={busy}>
            Bekor qilish
          </Button>
          <MainButton
            text="Ha, chetlatilsin"
            onClick={() => submit(state.slot, state.reason)}
            loading={busy}
            destructive
          />
        </>
      )}

      {state.step === "done" && (
        <>
          <CheatResult result={state.result} />
          <StudentSlotSection slot={state.slot} title="Talabgor" />
          <MainButton
            text="Yangi qidiruv"
            onClick={() => {
              setJshshir("");
              setState({ step: "search" });
            }}
          />
        </>
      )}
    </Screen>
  );
}

function ReasonTypePicker({ onPick }: { onPick: (type: ReasonType) => void }) {
  const types = useAsync(() => api.reasonTypes(), []);
  return (
    <Section title="Chetlatish turi">
      {types.loading && !types.data ? (
        <LoadingState />
      ) : types.error ? (
        <ErrorState message={types.error.message} onRetry={types.reload} />
      ) : !types.data?.length ? (
        <ErrorState message="Aktiv chetlatish turlari topilmadi." />
      ) : (
        types.data.map((type) => (
          <Row key={type.id} icon={<Ban />} tone="destructive" title={type.name} onClick={() => onPick(type)} />
        ))
      )}
    </Section>
  );
}

function ReasonPicker({ type, onPick }: { type: ReasonType; onPick: (reason: Reason) => void }) {
  const reasons = useAsync(() => api.reasons(type.id), [type.id]);
  return (
    <Section title={`Sabab • ${type.name}`}>
      {reasons.loading && !reasons.data ? (
        <LoadingState />
      ) : reasons.error ? (
        <ErrorState message={reasons.error.message} onRetry={reasons.reload} />
      ) : !reasons.data?.length ? (
        <ErrorState message="Bu tur uchun aktiv sabab topilmadi." />
      ) : (
        reasons.data.map((reason) => (
          <Row key={reason.id} title={reason.name} onClick={() => onPick(reason)} />
        ))
      )}
    </Section>
  );
}

function CheatResult({ result }: { result: CheatResponse }) {
  switch (result.status) {
    case "ok":
      return <Notice tone="success" title="Talabgor chetlatildi">{result.message}</Notice>;
    case "already_cheating":
      return <Notice tone="accent" title="Talabgor allaqachon chetlatilgan">{result.message}</Notice>;
    case "invalid_reason":
      return <Notice tone="warning" title="Sabab xato">{result.message}</Notice>;
    case "wrong_session":
      return <Notice tone="destructive" title="Sessiya mos kelmadi">{result.message}</Notice>;
    case "not_found":
      return <Notice tone="destructive" title="Talabgor topilmadi">{result.message}</Notice>;
    default:
      return <Notice tone="destructive" title="Xatolik">{result.message}</Notice>;
  }
}
