import { useEffect, useState } from "react";
import LookupCrudPage, { type Column, type FormField } from "../components/LookupCrudPage";
import { getReasonsListApi, createReasonApi, updateReasonApi, deleteReasonApi, getReasonTypesListApi } from "../api";
import type { LookupReasonTypeResponse } from "../interfaces";

export default function ReasonsPage() {
  const [reasonTypes, setReasonTypes] = useState<LookupReasonTypeResponse[]>([]);

  useEffect(() => {
    getReasonTypesListApi().then(setReasonTypes);
  }, []);

  const reasonTypeMap = Object.fromEntries(reasonTypes.map((rt) => [rt.id, rt.name]));

  const columns: Column[] = [
    { key: "id", label: "ID" },
    { key: "name", label: "Nomi" },
    { key: "key", label: "Kalit" },
    {
      key: "reason_type_id",
      label: "Sabab turi",
      render: (val: number | null) => (val ? reasonTypeMap[val] || `#${val}` : "—"),
    },
  ];

  const formFields: FormField[] = [
    { key: "name", label: "Nomi", type: "text", required: true },
    { key: "key", label: "Kalit", type: "number", required: true },
    {
      key: "reason_type_id",
      label: "Sabab turi",
      type: "select",
      required: false,
      options: reasonTypes.map((rt) => ({ value: rt.id, label: rt.name })),
    },
  ];

  return (
    <LookupCrudPage
      title="Sabablar ro'yxati"
      subtitle="Cheating sabablari ro'yxati"
      columns={columns}
      formFields={formFields}
      fetchAll={getReasonsListApi}
      createItem={createReasonApi}
      updateItem={updateReasonApi}
      deleteItem={deleteReasonApi}
    />
  );
}
