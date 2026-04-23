import { useEffect, useState } from "react";
import LookupCrudPage, { type Column, type FormField } from "../components/LookupCrudPage";
import { getZonesListApi, createZoneApi, updateZoneApi, deleteZoneApi, getRegionsListApi } from "../api";
import type { LookupRegionResponse } from "../interfaces";
import { PERM } from "../permissions";

export default function ZonesPage() {
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);

  useEffect(() => {
    getRegionsListApi()
      .then(setRegions)
      .catch((err) => console.error("Hududlar ro'yxatini yuklashda xatolik", err));
  }, []);

  const regionMap = Object.fromEntries(regions.map((r) => [r.id, r.name]));

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
      createItem={createZoneApi}
      updateItem={updateZoneApi}
      deleteItem={deleteZoneApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
