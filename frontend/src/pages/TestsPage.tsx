import LookupCrudPage from "../components/LookupCrudPage";
import { getTestsListApi, createTestApi, updateTestApi, deleteTestApi } from "../api";

export default function TestsPage() {
  return (
    <LookupCrudPage
      title="Testlar"
      subtitle="Test nomlari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "text", required: true },
      ]}
      fetchAll={getTestsListApi}
      createItem={createTestApi}
      updateItem={updateTestApi}
      deleteItem={deleteTestApi}
    />
  );
}
