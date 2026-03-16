import LookupCrudPage from "../components/LookupCrudPage";
import { getReasonTypesListApi, createReasonTypeApi, updateReasonTypeApi, deleteReasonTypeApi } from "../api";

export default function ReasonTypesPage() {
  return (
    <LookupCrudPage
      title="Sabab guruhlari"
      subtitle="Sabab turlari guruhlari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "number", required: true },
      ]}
      fetchAll={getReasonTypesListApi}
      createItem={createReasonTypeApi}
      updateItem={updateReasonTypeApi}
      deleteItem={deleteReasonTypeApi}
    />
  );
}
