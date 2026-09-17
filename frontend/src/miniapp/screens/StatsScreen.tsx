import { useEffect, useState } from "react";
import { api } from "../api";
import { AttendanceSummary } from "../components/AttendanceSummary";
import { Building } from "../components/icons";
import {
  Card,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingState,
  MainButton,
  ProgressBar,
  Screen,
  Section,
} from "../components/ui";
import { useApp } from "../context";
import { useAsync, useSendAbsentees } from "../hooks";
import type { ReadySession, StatsScope, ZoneStat } from "../types";
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

function ZoneRow({ zone }: { zone: ZoneStat }) {
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
    </div>
  );
}

export function StatsScreen({ session, scope }: { session: ReadySession; scope: StatsScope }) {
  const { region } = useApp();
  const stats = useAsync(() => api.stats(session.id, scope, region.id), [session.id, scope, region.id]);
  const absentees = useSendAbsentees(session.id, scope);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const { title, subtitle } = scopeTitle(scope);

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
        stats.data.regions.map((regionStat) => {
          // Shu kontekstda talabgori yo'q binolar (0 / 0) — faqat shovqin.
          const zones = regionStat.zones.filter((zone) => zone.total > 0);
          return (
            <div key={regionStat.region_id} className="space-y-6">
              <AttendanceSummary title={regionStat.region_name} counts={regionStat} />
              {zones.length > 0 && (
                <Section
                  title={`Binolar (${zones.length})`}
                  footer={updatedAt ? `Oxirgi yangilanish: ${formatTime(updatedAt)}` : undefined}
                >
                  {zones.map((zone) => (
                    <ZoneRow key={zone.zone_id} zone={zone} />
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
