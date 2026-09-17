import type { StudentSlot } from "../types";
import { formatDay } from "../utils/format";
import { ChevronRight } from "./icons";
import { DetailRow, Section } from "./ui";

/** Smena nomida raqam odatda bor ("1-Smena") — takrorlamaymiz. */
function smenaLabel(slot: StudentSlot): string {
  if (slot.smena_name) return slot.smena_name;
  return slot.smena_number ? `${slot.smena_number}-smena` : "—";
}

/** Talabgorning test joyi — bot formatteridagi `_format_slot_block` bilan bir xil maydonlar. */
export function StudentSlotSection({ slot, title }: { slot: StudentSlot; title?: string }) {
  return (
    <Section title={title}>
      <DetailRow label="FIO" value={<span className="font-semibold">{slot.fio || "—"}</span>} />
      <DetailRow label="JShShIR" value={slot.jshshir || "—"} mono />
      <DetailRow label="Viloyat" value={slot.region_name || "—"} />
      <DetailRow label="Bino" value={slot.zone_name || "—"} />
      <DetailRow label="Sana" value={slot.test_day ? formatDay(slot.test_day) : "—"} />
      <DetailRow label="Smena" value={smenaLabel(slot)} />
      {!!slot.gr_n && (
        <DetailRow
          label="Guruh / joy"
          value={`${slot.gr_n}-guruh${slot.sp_n ? ` • ${slot.sp_n}-joy` : ""}`}
        />
      )}
      {slot.subject_name && <DetailRow label="Fan" value={slot.subject_name} />}
    </Section>
  );
}

/** JShShIR bo'yicha bir nechta yozuv chiqqanda — tanlash ro'yxati. */
export function StudentSlotPicker({
  slots,
  onPick,
}: {
  slots: StudentSlot[];
  onPick: (slot: StudentSlot) => void;
}) {
  return (
    <Section
      title={`${slots.length} ta yozuv topildi`}
      footer="Bu JShShIR bir nechta fan yoki smenada qatnashadi. Kerakli yozuvni tanlang."
    >
      {slots.map((slot) => (
        <button
          key={slot.student_id}
          type="button"
          onClick={() => onPick(slot)}
          className="tg-pressable flex w-full items-center gap-3 px-4 py-3 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="block text-[16px] font-medium text-tg-text">{slot.fio || "—"}</span>
            <span className="mt-0.5 block text-[13px] leading-snug text-tg-hint">
              {[
                slot.test_day && formatDay(slot.test_day),
                slot.smena_name,
                slot.gr_n ? `${slot.gr_n}-guruh` : null,
                slot.sp_n ? `${slot.sp_n}-joy` : null,
              ]
                .filter(Boolean)
                .join(" • ")}
            </span>
            {(slot.subject_name || slot.zone_name) && (
              <span className="mt-0.5 block text-[13px] leading-snug text-tg-hint">
                {[slot.zone_name, slot.subject_name].filter(Boolean).join(" • ")}
              </span>
            )}
          </span>
          <span className="text-tg-hint">
            <ChevronRight width={18} height={18} />
          </span>
        </button>
      ))}
    </Section>
  );
}
