import LookupCrudPage from "../components/LookupCrudPage";
import { getRolesListApi, createRoleApi, updateRoleApi, deleteRoleApi } from "../api";
import { PERM } from "../permissions";

export default function RolesPage() {
  return (
    <LookupCrudPage
      title="Rollar"
      subtitle="Foydalanuvchi rollari"
      columns={[
        { key: "id", label: "ID" },
        { key: "name", label: "Nomi" },
        { key: "key", label: "Kalit" },
      ]}
      formFields={[
        { key: "name", label: "Nomi", type: "text", required: true },
        { key: "key", label: "Kalit", type: "number", required: true },
      ]}
      fetchAll={getRolesListApi}
      createItem={createRoleApi}
      updateItem={updateRoleApi}
      deleteItem={deleteRoleApi}
      createPermission={PERM.ROLE_CREATE}
      updatePermission={PERM.ROLE_UPDATE}
      deletePermission={PERM.ROLE_DELETE}
    />
  );
}
