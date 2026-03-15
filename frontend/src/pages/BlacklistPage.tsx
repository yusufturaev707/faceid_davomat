import LookupCrudPage from "../components/LookupCrudPage";
import { getBlacklistApi, createBlacklistApi, updateBlacklistApi, deleteBlacklistApi } from "../api";

export default function BlacklistPage() {
  return (
    <LookupCrudPage
      title="Qora ro'yxat"
      subtitle="Bloklangan talabalar (IMEI bo'yicha)"
      columns={[
        { key: "id", label: "ID" },
        { key: "imei", label: "IMEI" },
        { key: "description", label: "Izoh" },
      ]}
      formFields={[
        { key: "imei", label: "IMEI", type: "text", placeholder: "14 raqamli IMEI" },
        { key: "description", label: "Izoh", type: "text", placeholder: "Sabab..." },
      ]}
      fetchAll={getBlacklistApi}
      createItem={createBlacklistApi}
      updateItem={updateBlacklistApi}
      deleteItem={deleteBlacklistApi}
    />
  );
}
