import LookupCrudPage from "../components/LookupCrudPage";
import { getReasonsListApi, createReasonApi, updateReasonApi, deleteReasonApi } from "../api";

export default function ReasonsPage() {
  return (
    <LookupCrudPage
      title="Sabab turlari"
      subtitle="Cheating sabablari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "number", required: true },
      ]}
      fetchAll={getReasonsListApi}
      createItem={createReasonApi}
      updateItem={updateReasonApi}
      deleteItem={deleteReasonApi}
    />
  );
}
