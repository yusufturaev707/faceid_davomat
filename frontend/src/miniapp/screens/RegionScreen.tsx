import { CheckCircle, MapPin } from "../components/icons";
import { Row, Screen, Section } from "../components/ui";
import { useApp } from "../context";
import { useNavigation } from "../navigation";
import { telegram } from "../telegram";
import type { Region } from "../types";

/** Viloyat tanlash. Tanlangan viloyat kesimida statistika, Face ID va qidiruv ishlaydi. */
export function RegionScreen({
  regions,
  currentId,
  onSelect,
  fio,
}: {
  regions: Region[];
  currentId: number | null;
  onSelect: (regionId: number) => void;
  fio?: string;
}) {
  return (
    <Screen
      title={fio ? `Assalomu alaykum, ${fio}!` : "Viloyatni tanlang"}
      subtitle="Qaysi viloyat bo'yicha ishlaysiz? Keyin bosh sahifadan istalgan vaqtda almashtirish mumkin."
    >
      <Section title="Biriktirilgan viloyatlar">
        {regions.map((region) => {
          const active = region.id === currentId;
          return (
            <Row
              key={region.id}
              icon={<MapPin />}
              tone={active ? "success" : "accent"}
              title={region.name}
              chevron={false}
              after={
                active ? (
                  <span className="text-tg-success">
                    <CheckCircle />
                  </span>
                ) : undefined
              }
              onClick={() => {
                telegram.haptic("success");
                onSelect(region.id);
              }}
            />
          );
        })}
      </Section>
    </Screen>
  );
}

export function RegionRouteScreen() {
  const { regions, region, selectRegion } = useApp();
  const nav = useNavigation();
  return (
    <RegionScreen
      regions={regions}
      currentId={region.id}
      onSelect={(id) => {
        selectRegion(id);
        nav.back();
      }}
    />
  );
}
