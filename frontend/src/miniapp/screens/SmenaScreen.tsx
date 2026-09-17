import { useMemo } from "react";
import { api } from "../api";
import { AttendanceSummary } from "../components/AttendanceSummary";
import { Ban, BarChart, FileDown, ScanFace, UserMinus } from "../components/icons";
import { Card, ErrorState, LoadingState, Row, Screen, Section } from "../components/ui";
import { useApp } from "../context";
import { useAsync, useSendAbsentees } from "../hooks";
import { useNavigation } from "../navigation";
import type { ReadySession, SmenaInfo, StatsScope } from "../types";
import { formatDay, sumCounts } from "../utils/format";

/** Kun+smena tanlangach — bot'dagi amallar menyusi, tepada jonli davomat. */
export function SmenaScreen({ session, smena }: { session: ReadySession; smena: SmenaInfo }) {
  const { region } = useApp();
  const nav = useNavigation();
  const scope = useMemo<StatsScope>(() => ({ kind: "smena", smena }), [smena]);
  const stats = useAsync(() => api.stats(session.id, scope, region.id), [session.id, scope, region.id]);
  const absentees = useSendAbsentees(session.id, scope);

  const openStats = () => nav.push({ name: "stats", session, scope });

  return (
    <Screen title={smena.smena_name} subtitle={`${formatDay(smena.day)} • ${session.name}`}>
      {stats.loading && !stats.data ? (
        <Card>
          <LoadingState label="Davomat yuklanmoqda..." />
        </Card>
      ) : stats.error ? (
        <Card>
          <ErrorState message={stats.error.message} onRetry={stats.reload} />
        </Card>
      ) : (
        stats.data && (
          <AttendanceSummary
            title={`${region.name} • batafsil uchun bosing`}
            counts={sumCounts(stats.data.regions)}
            onClick={openStats}
          />
        )
      )}

      <Section title="Talabgor bilan ishlash">
        <Row
          icon={<ScanFace />}
          title="Face ID"
          subtitle="Pasport + selfi tekshiruvi va davomatga qo'shish"
          onClick={() => nav.push({ name: "faceid", session, smena })}
        />
        <Row
          icon={<UserMinus />}
          tone="warning"
          title="Davomatdan olib tashlash"
          subtitle="JShShIR bo'yicha, faqat shu smenada"
          onClick={() => nav.push({ name: "remove", session, smena })}
        />
        <Row
          icon={<Ban />}
          tone="destructive"
          title="Chetlatish"
          subtitle="JShShIR bo'yicha, butun test tadbirida"
          onClick={() => nav.push({ name: "cheat", session, smena })}
        />
      </Section>

      <Section title="Hisobotlar" footer="Excel fayl bot orqali Telegram chatingizga yuboriladi.">
        <Row
          icon={<BarChart />}
          tone="success"
          title="Davomat statistikasi"
          subtitle="Bino kesimida"
          onClick={openStats}
        />
        <Row
          icon={<FileDown />}
          tone="neutral"
          title="Kelmaganlar ro'yxati"
          subtitle="Excel → Telegram chat"
          onClick={absentees.send}
          loading={absentees.sending}
          chevron={false}
        />
      </Section>
    </Screen>
  );
}
