import { BarChart, Clock, Layers } from "../components/icons";
import { EmptyState, Row, Screen, Section } from "../components/ui";
import { useNavigation } from "../navigation";
import type { ReadySession } from "../types";
import { formatDay, formatWeekday, groupSmenasByDay } from "../utils/format";

/** Sessiya → kunlar → smenalar. Har kun oxirida kun yakuni, eng pastda umumiy statistika. */
export function SessionScreen({ session }: { session: ReadySession }) {
  const nav = useNavigation();
  const days = groupSmenasByDay(session.smenas);

  return (
    <Screen
      title={session.name}
      subtitle={[session.test_name, `${formatDay(session.start_date)} — ${formatDay(session.finish_date)}`]
        .filter(Boolean)
        .join(" • ")}
    >
      {days.length === 0 ? (
        <Section>
          <EmptyState icon={<Layers width={32} height={32} />} title="Bu test tadbirida smena yo'q" />
        </Section>
      ) : (
        days.map(({ day, smenas }) => (
          <Section key={day} title={`${formatDay(day)} • ${formatWeekday(day)}`}>
            {smenas.map((smena) => (
              <Row
                key={smena.id}
                icon={<Clock />}
                title={smena.smena_name}
                subtitle="Face ID, davomat, chetlatish"
                onClick={() => nav.push({ name: "smena", session, smena })}
              />
            ))}
            <Row
              icon={<BarChart />}
              tone="neutral"
              title="Kun yakuni"
              subtitle="Shu kunning barcha smenalari bo'yicha"
              onClick={() => nav.push({ name: "stats", session, scope: { kind: "day", day } })}
            />
          </Section>
        ))
      )}

      {days.length > 0 && (
        <Section>
          <Row
            icon={<BarChart />}
            tone="success"
            title="Umumiy statistika"
            subtitle="Barcha kunlar va smenalar bo'yicha"
            onClick={() => nav.push({ name: "stats", session, scope: { kind: "total" } })}
          />
        </Section>
      )}
    </Screen>
  );
}
