import { api } from "../api";
import { Calendar, MapPin, User } from "../components/icons";
import { EmptyState, ErrorState, IconButton, LoadingState, Row, Screen, Section } from "../components/ui";
import { useApp } from "../context";
import { useAsync } from "../hooks";
import { useNavigation } from "../navigation";
import { formatDay } from "../utils/format";

export function HomeScreen() {
  const { operator, region, regions } = useApp();
  const nav = useNavigation();
  const sessions = useAsync(() => api.sessions(), []);
  const canChangeRegion = regions.length > 1;

  return (
    <Screen
      title="Davomat"
      subtitle="Test tadbirlari davomati, Face ID va chetlatish"
      action={<IconButton label="Yangilash" onClick={sessions.reload} loading={sessions.loading} />}
    >
      <Section>
        <Row
          icon={<User />}
          title={<span className="font-semibold">{operator.fio}</span>}
          subtitle={operator.role?.name}
        />
        <Row
          icon={<MapPin />}
          tone="success"
          title={region.name}
          subtitle={canChangeRegion ? "Joriy viloyat • almashtirish uchun bosing" : "Joriy viloyat"}
          onClick={canChangeRegion ? () => nav.push({ name: "regions" }) : undefined}
        />
      </Section>

      <Section title="Faol test tadbirlari">
        {sessions.loading && !sessions.data ? (
          <LoadingState />
        ) : sessions.error ? (
          <ErrorState message={sessions.error.message} onRetry={sessions.reload} />
        ) : !sessions.data?.length ? (
          <EmptyState
            icon={<Calendar width={32} height={32} />}
            title="Faol test tadbirlari yo'q"
            text="Test sessiyasi «Tayyor» holatiga o'tgach shu yerda paydo bo'ladi."
          />
        ) : (
          sessions.data.map((session) => (
            <Row
              key={session.id}
              icon={<Calendar />}
              title={session.name}
              subtitle={
                <>
                  {session.test_name && <span className="block">{session.test_name}</span>}
                  <span className="block">
                    {formatDay(session.start_date)} — {formatDay(session.finish_date)} •{" "}
                    {session.smenas.length} ta smena
                  </span>
                </>
              }
              onClick={() => nav.push({ name: "session", session })}
            />
          ))
        )}
      </Section>
    </Screen>
  );
}
