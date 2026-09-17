/**
 * Davomatdan olib tashlash: JShShIR → (bir nechta bo'lsa tanlash) → tasdiqlash.
 * Faqat tanlangan smenada va hozir davomatda turganlar qidiriladi. Backend
 * faqat `Student.is_entered=False` qiladi — StudentLog tarixi saqlanadi.
 */

import { useState } from "react";
import { api } from "../api";
import { JshshirSearch } from "../components/JshshirSearch";
import { StudentSlotPicker, StudentSlotSection } from "../components/StudentSlot";
import { Button, MainButton, Notice, Screen, useToast } from "../components/ui";
import { useApp } from "../context";
import { useBackHandler } from "../navigation";
import { telegram } from "../telegram";
import type { RemoveAttendanceResponse, SmenaInfo, StudentSlot } from "../types";
import { formatDay } from "../utils/format";

type State =
  | { step: "search"; notFound?: string }
  | { step: "pick"; matches: StudentSlot[] }
  | { step: "confirm"; slot: StudentSlot; matches: StudentSlot[] }
  | { step: "done"; result: RemoveAttendanceResponse; slot: StudentSlot };

export function RemoveScreen({ smena }: { smena: SmenaInfo }) {
  const { region } = useApp();
  const toast = useToast();
  const [state, setState] = useState<State>({ step: "search" });
  const [jshshir, setJshshir] = useState("");
  const [busy, setBusy] = useState(false);

  useBackHandler(() => {
    if (busy) return true;
    if (state.step === "confirm") {
      setState(state.matches.length > 1 ? { step: "pick", matches: state.matches } : { step: "search" });
      return true;
    }
    if (state.step === "pick") {
      setState({ step: "search" });
      return true;
    }
    return false;
  });

  const search = async (value: string) => {
    setJshshir(value);
    setBusy(true);
    try {
      const response = await api.findByJshshir(smena.id, region.id, value);
      if (response.status !== "ok" || response.matches.length === 0) {
        telegram.haptic("warning");
        setState({ step: "search", notFound: response.message || "Talabgor topilmadi." });
      } else if (response.matches.length === 1) {
        setState({ step: "confirm", slot: response.matches[0], matches: response.matches });
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

  const remove = async (slot: StudentSlot) => {
    setBusy(true);
    try {
      const result = await api.removeAttendance(slot.student_id, smena.id, region.id);
      telegram.haptic(result.status === "ok" ? "success" : "warning");
      setState({ step: "done", result, slot });
    } catch (err) {
      telegram.haptic("error");
      toast((err as Error).message, "destructive");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="Davomatdan olib tashlash" subtitle={`${smena.smena_name} • ${formatDay(smena.day)}`}>
      {state.step === "search" && (
        <>
          {state.notFound && <Notice tone="warning" title="Topilmadi">{state.notFound}</Notice>}
          <JshshirSearch
            key={state.notFound ?? "search"}
            initial={jshshir}
            loading={busy}
            footer="Talabgor faqat shu smenada, davomatga qo'shilganlar orasidan qidiriladi."
            onSearch={search}
          />
        </>
      )}

      {state.step === "pick" && (
        <StudentSlotPicker
          slots={state.matches}
          onPick={(slot) => setState({ step: "confirm", slot, matches: state.matches })}
        />
      )}

      {state.step === "confirm" && (
        <>
          <Notice tone="warning" title="Davomatdan olib tashlashni tasdiqlang">
            Talabgor davomatdan chiqariladi. Kirish tarixi (selfi, vaqt) saqlanib qoladi.
          </Notice>
          <StudentSlotSection slot={state.slot} title="Talabgor" />
          <Button variant="plain" onClick={() => setState({ step: "search" })} disabled={busy}>
            Bekor qilish
          </Button>
          <MainButton
            text="Ha, olib tashlansin"
            onClick={() => remove(state.slot)}
            loading={busy}
            destructive
          />
        </>
      )}

      {state.step === "done" && (
        <>
          <RemoveResult result={state.result} />
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

function RemoveResult({ result }: { result: RemoveAttendanceResponse }) {
  switch (result.status) {
    case "ok":
      return <Notice tone="success" title="Muvaffaqiyatli bajarildi">{result.message}</Notice>;
    case "not_entered":
      return <Notice tone="accent" title="Talabgor davomatda emas edi">{result.message}</Notice>;
    case "not_found":
      return <Notice tone="destructive" title="Talabgor topilmadi">{result.message}</Notice>;
    default:
      return <Notice tone="destructive" title="Xatolik">{result.message}</Notice>;
  }
}
