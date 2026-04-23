import LookupCrudPage from "../components/LookupCrudPage";
import { getGendersListApi, createGenderApi, updateGenderApi, deleteGenderApi } from "../api";
import { PERM } from "../permissions";

export default function GendersPage() {
  return (
    <LookupCrudPage
      title="Jinslar"
      subtitle="Jins turlari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "number", required: true },
      ]}
      fetchAll={getGendersListApi}
      createItem={createGenderApi}
      updateItem={updateGenderApi}
      deleteItem={deleteGenderApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
