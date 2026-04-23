import LookupCrudPage from "../components/LookupCrudPage";
import { getSmenasListApi, createSmenaApi, updateSmenaApi, deleteSmenaApi } from "../api";
import { PERM } from "../permissions";

export default function SmenasPage() {
  return (
    <LookupCrudPage
      title="Smenalar"
      subtitle="Test smenalari ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "number", label: "Raqam" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "number", label: "Raqam", type: "number", required: true },
      ]}
      fetchAll={getSmenasListApi}
      createItem={createSmenaApi}
      updateItem={updateSmenaApi}
      deleteItem={deleteSmenaApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
