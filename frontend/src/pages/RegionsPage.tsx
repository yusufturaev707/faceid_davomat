import LookupCrudPage from "../components/LookupCrudPage";
import {
  getRegionsListApi,
  createRegionApi,
  updateRegionApi,
  deleteRegionApi,
} from "../api";
import { PERM } from "../permissions";

export default function RegionsPage() {
  return (
    <LookupCrudPage
      title="Viloyatlar"
      subtitle="Viloyatlar ro'yxati"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "number", label: "Dtm nomer" },
        { key: "s_number", label: "S nomer" },
        { key: "k_number", label: "VM nomer" },
        { key: "is_have_part", label: "Qo'shimcha hududli" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "number", label: "Dtm nomer", type: "number", required: true },
        { key: "s_number", label: "S nomer", type: "number", required: true },
        { key: "k_number", label: "VM nomer", type: "number", required: true },
        {
          key: "is_have_part",
          label: "Qo'shimcha hududi bormi?",
          type: "checkbox",
        },
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
