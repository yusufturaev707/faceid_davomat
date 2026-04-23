import LookupCrudPage from "../components/LookupCrudPage";
import { getSessionStatesListApi, createSessionStateApi, updateSessionStateApi, deleteSessionStateApi } from "../api";
import { PERM } from "../permissions";

export default function SessionStatesPage() {
  return (
    <LookupCrudPage
      title="Sessiya holatlari"
      subtitle="Test sessiya holatlari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "number", required: true },
      ]}
      fetchAll={getSessionStatesListApi}
      createItem={createSessionStateApi}
      updateItem={updateSessionStateApi}
      deleteItem={deleteSessionStateApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
