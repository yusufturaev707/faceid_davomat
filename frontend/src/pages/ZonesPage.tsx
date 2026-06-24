import { useCallback, useEffect, useState } from "react";
import LookupCrudPage, { type Column, type FormField } from "../components/LookupCrudPage";
import { getZonesListApi, createZoneApi, updateZoneApi, deleteZoneApi, getRegionsListApi } from "../api";
import type { LookupRegionResponse, LookupZoneResponse } from "../interfaces";
import { PERM } from "../permissions";

export default function ZonesPage() {
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);

  useEffect(() => {
    getRegionsListApi()
      .then(setRegions)
      .catch((err) => console.error("Hududlar ro'yxatini yuklashda xatolik", err));
  }, []);

  const regionMap = Object.fromEntries(regions.map((r) => [r.id, r.name]));

  // Tartib: avval viloyat raqami (region.number), so'ng shu viloyatning bino
  // raqami (zone.number) bo'yicha. Viloyat raqami topilmasa oxiriga suriladi.
  const sortItems = useCallback(
    (items: LookupZoneResponse[]) => {
      const numMap = new Map(regions.map((r) => [r.id, r.number]));
      return [...items].sort((a, b) => {
        const ra = numMap.get(a.region_id) ?? Number.MAX_SAFE_INTEGER;
        const rb = numMap.get(b.region_id) ?? Number.MAX_SAFE_INTEGER;
        if (ra !== rb) return ra - rb;
        return (a.number ?? 0) - (b.number ?? 0);
      });
    },
    [regions],
  );

  const columns: Column[] = [
    { key: "id", label: "ID" },
    { key: "name", label: "Nomi" },
    { key: "number", label: "Raqam" },
    {
      key: "region_id",
      label: "Hudud",
      render: (val: number) => regionMap[val] || `#${val}`,
    },
  ];

  const formFields: FormField[] = [
    { key: "name", label: "Nomi", type: "text", required: true },
    { key: "number", label: "Raqam", type: "number", required: true },
    {
      key: "region_id",
      label: "Hudud",
      type: "select",
      required: true,
      options: regions.map((r) => ({ value: r.id, label: r.name })),
    },
  ];

  return (
    <LookupCrudPage
      title="Binolar"
      subtitle="Test o'tkazish binolari"
      columns={columns}
      formFields={formFields}
      fetchAll={getZonesListApi}
      sortItems={sortItems}
      createItem={createZoneApi}
      updateItem={updateZoneApi}
      deleteItem={deleteZoneApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
