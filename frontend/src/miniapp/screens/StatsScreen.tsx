import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { AttendanceSummary } from "../components/AttendanceSummary";
import { Building, CheckCircle, ChevronRight, Send } from "../components/icons";
import {
  Card,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingState,
  MainButton,
  ProgressBar,
  Row,
  Screen,
  Section,
} from "../components/ui";
import { useApp } from "../context";
import { useAsync, useSendAbsentees, useSendStatsReport } from "../hooks";
import type { FullGroup, ReadySession, SmenaInfo, StatsScope, ZoneStat } from "../types";
import { attendancePercent, formatDay, formatNumber, formatTime } from "../utils/format";

function scopeTitle(scope: StatsScope): { title: string; subtitle: string } {
  switch (scope.kind) {
    case "smena":
      return { title: scope.smena.smena_name, subtitle: formatDay(scope.smena.day) };
    case "day":
      return { title: "Kun yakuni", subtitle: `${formatDay(scope.day)} • barcha smenalar` };
    case "total":
      return { title: "Umumiy statistika", subtitle: "Barcha kunlar va smenalar" };
  }
}

/** Yig'iq holatda ko'rinadigan guruh chiplari soni (bitta smena). */
const GROUPS_PREVIEW = 12;

function GroupChip({ group }: { group: FullGroup }) {
  return (
    <span
      title={`${group.gr_n}-guruh • ${group.total} ta talabgor${group.cheating ? ` (${group.cheating} chetlatilgan)` : ""}`}
      className="tg-tint-success relative inline-flex h-7 min-w-[2.25rem] items-center justify-center rounded-lg px-2 text-[13px] font-semibold tabular-nums text-tg-success"
    >
      {group.gr_n}
      {group.cheating > 0 && (
        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-tg-destructive" aria-hidden />
      )}
    </span>
  );
}

/**
 * Bino ichida hamma talabgori kelgan guruhlar — guruh raqami bo'yicha.
 * Bitta smenada: birinchi `GROUPS_PREVIEW` ta chip, bosilsa hammasi.
 * Kun/umumiy ko'lamda: smenalar bo'yicha soni, bosilsa har smena chiplari.
 */
function FullGroups({ zone, smenas }: { zone: ZoneStat; smenas: Map<number, SmenaInfo> | null }) {
  const [open, setOpen] = useState(false);
  const full = zone.full_groups ?? [];

  const sections = useMemo(() => {
    if (!smenas) return [];
    const bySmena = new Map<number, FullGroup[]>();
    for (const g of full) {
      const list = bySmena.get(g.session_smena_id);
      if (list) list.push(g);
      else bySmena.set(g.session_smena_id, [g]);
    }
    const order = (id: number) => {
      const s = smenas.get(id);
      return s ? `${s.day}|${String(s.smena_number).padStart(3, "0")}` : `~${id}`;
    };
    return [...bySmena.entries()].sort(([a], [b]) => order(a).localeCompare(order(b)));
  }, [full, smenas]);

  if (!zone.total_groups) return null;
  const expandable = smenas ? full.length > 0 : full.length > GROUPS_PREVIEW;
  const shown = open ? full : full.slice(0, GROUPS_PREVIEW);
  const toggle = () => setOpen((v) => !v);

  return (
    <div className="mt-3 rounded-xl bg-tg-secondary px-3 py-2.5">
      <button
        type="button"
        onClick={expandable ? toggle : undefined}
        aria-expanded={expandable ? open : undefined}
        className="flex w-full items-center justify-between gap-2 text-left text-[13px]"
      >
        <span className="flex items-center gap-1.5 font-medium text-tg-success">
          <CheckCircle width={16} height={16} />
          100% kelgan guruhlar
        </span>
        <span className="flex items-center gap-1 tabular-nums text-tg-hint">
          <b className="text-tg-success">{full.length}</b> / {zone.total_groups}
          {expandable && (
            <ChevronRight
              width={16}
              height={16}
              className={`transition-transform duration-200 ${open ? "-rotate-90" : "rotate-90"}`}
            />
          )}
        </span>
      </button>

      {full.length === 0 ? (
        <p className="mt-1.5 text-[12px] text-tg-hint">Hozircha to'liq kelgan guruh yo'q</p>
      ) : smenas ? (
        <div className="mt-2 space-y-2">
          {sections.map(([smenaId, list]) => {
            const s = smenas.get(smenaId);
            return (
              <div key={smenaId}>
                <p className="flex justify-between gap-2 text-[12px] text-tg-hint">
                  <span className="truncate">{s ? `${formatDay(s.day)} • ${s.smena_name}` : `Smena #${smenaId}`}</span>
                  <span className="shrink-0 tabular-nums">{list.length} ta</span>
                </p>
                {open && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {list.map((g) => (
                      <GroupChip key={g.gr_n} group={g} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {shown.map((g) => (
            <GroupChip key={g.gr_n} group={g} />
          ))}
          {full.length > shown.length && (
            <button
              type="button"
              onClick={toggle}
              className="tg-tint inline-flex h-7 items-center rounded-lg px-2 text-[13px] font-semibold text-tg-button"
            >
              +{full.length - shown.length}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ZoneRow({ zone, smenas }: { zone: ZoneStat; smenas: Map<number, SmenaInfo> | null }) {
  const percent = attendancePercent(zone);
  return (
    <div className="px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 flex-1 text-[15px] font-medium leading-snug text-tg-text">{zone.zone_name}</p>
        <p className="shrink-0 text-[15px] font-semibold tabular-nums text-tg-text">{percent}%</p>
      </div>
      <div className="mt-2">
        <ProgressBar value={percent} />
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] tabular-nums text-tg-hint">
        <span>
          Keldi <b className="text-tg-text">{formatNumber(zone.entered)}</b> / {formatNumber(zone.total)}
        </span>
        <span>
          Kelmagan <b className="text-tg-warning">{formatNumber(zone.not_entered)}</b>
        </span>
        {zone.cheating > 0 && (
          <span>
            Chetlatilgan <b className="text-tg-destructive">{formatNumber(zone.cheating)}</b>
          </span>
        )}
      </div>
      <FullGroups zone={zone} smenas={smenas} />
    </div>
  );
}

export function StatsScreen({ session, scope }: { session: ReadySession; scope: StatsScope }) {
  const { region } = useApp();
  const stats = useAsync(() => api.stats(session.id, scope, region.id), [session.id, scope, region.id]);
  const absentees = useSendAbsentees(session.id, scope);
  const report = useSendStatsReport(session.id, scope);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const { title, subtitle } = scopeTitle(scope);
  // Kun/umumiy ko'lamda guruhlar smenalar bo'yicha ajratiladi (bitta smenada — yo'q).
  const smenas = useMemo(
    () => (scope.kind === "smena" ? null : new Map(session.smenas.map((s) => [s.id, s]))),
    [scope.kind, session.smenas],
  );

  useEffect(() => {
    if (stats.data) setUpdatedAt(new Date());
  }, [stats.data]);

  return (
    <Screen
      title={title}
      subtitle={`${subtitle} • ${session.name}`}
      action={<IconButton label="Yangilash" onClick={stats.reload} loading={stats.loading} />}
    >
      {stats.loading && !stats.data ? (
        <Card>
          <LoadingState label="Statistika tayyorlanmoqda..." />
        </Card>
      ) : stats.error ? (
        <Card>
          <ErrorState message={stats.error.message} onRetry={stats.reload} />
        </Card>
      ) : !stats.data?.regions.length ? (
        <Card>
          <EmptyState icon={<Building width={32} height={32} />} title="Ma'lumot topilmadi" />
        </Card>
      ) : (
        stats.data.regions.map((regionStat, index) => {
          // Shu kontekstda talabgori yo'q binolar (0 / 0) — faqat shovqin.
          const zones = regionStat.zones.filter((zone) => zone.total > 0);
          return (
            <div key={regionStat.region_id} className="space-y-6">
              <AttendanceSummary title={regionStat.region_name} counts={regionStat} />
              {index === 0 && (
                <Section footer="Ayni vaqtdagi holat bot chatiga xabar bo'lib keladi — uni guruhga forward qiling.">
                  <Row
                    icon={<Send />}
                    title="Davomatni guruhga yuborish"
                    subtitle="Viloyat va binolar kesimida"
                    onClick={report.send}
                    loading={report.sending}
                    chevron={false}
                  />
                </Section>
              )}
              {zones.length > 0 && (
                <Section
                  title={`Binolar (${zones.length})`}
                  footer={updatedAt ? `Oxirgi yangilanish: ${formatTime(updatedAt)}` : undefined}
                >
                  {zones.map((zone) => (
                    <ZoneRow key={zone.zone_id} zone={zone} smenas={smenas} />
                  ))}
                </Section>
              )}
            </div>
          );
        })
      )}

      <MainButton
        text="Kelmaganlar ro'yxati (Excel)"
        onClick={absentees.send}
        loading={absentees.sending}
        disabled={!stats.data}
      />
    </Screen>
  );
}
