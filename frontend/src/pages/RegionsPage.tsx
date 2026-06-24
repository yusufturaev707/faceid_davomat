import LookupCrudPage from "../components/LookupCrudPage";
import { getRegionsListApi, createRegionApi, updateRegionApi, deleteRegionApi } from "../api";
import { PERM } from "../permissions";

export default function RegionsPage() {
  return (
    <LookupCrudPage
      title="Hududlar"
      subtitle="Hududlar (viloyatlar) ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "number", label: "Raqam" },
        { key: "s_number", label: "S-raqam" },
        { key: "k_number", label: "K-raqam" },
        { key: "is_have_part", label: "Bo'limli" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "number", label: "Raqam", type: "number", required: true },
        { key: "s_number", label: "S-raqam", type: "number", required: true },
        { key: "k_number", label: "K-raqam", type: "number", required: true },
        { key: "is_have_part", label: "Bo'limlarga bo'lingan", type: "checkbox" },
      ]}
      fetchAll={getRegionsListApi}
      createItem={createRegionApi}
      updateItem={updateRegionApi}
      deleteItem={deleteRegionApi}
      createPermission={PERM.LOOKUP_CREATE}
      updatePermission={PERM.LOOKUP_UPDATE}
      deletePermission={PERM.LOOKUP_DELETE}
    />
  );
}
