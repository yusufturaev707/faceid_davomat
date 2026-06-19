import { useEffect, useMemo, useState } from "react";
import type { UserResponse, CreateUserRequest, UpdateUserRequest, LookupRoleResponse, LookupRegionResponse, LookupZoneResponse } from "../interfaces";
import { getUsersApi, createUserApi, updateUserApi, deleteUserApi, getRolesListApi, getRegionsListApi, getZonesListApi, getZonesByRegionApi } from "../api";
import { useAuth } from "../contexts/AuthContext";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import PermissionGate from "../components/PermissionGate";
import Md3Select from "../components/Md3Select";
import { PERM } from "../permissions";
import { extractErrorMessage } from "../utils/errorMessage";

const PAGE_SIZE = 20;

// Admin role yagona "super-protected" rol — uni faqat user id=1 boshqaradi.
const ADMIN_ROLE_KEY = 1;
const SUPER_ADMIN_USER_ID = 1;

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const isSuperAdmin = currentUser?.id === SUPER_ADMIN_USER_ID;

  const [users, setUsers] = useState<UserResponse[]>([]);
  const [roles, setRoles] = useState<LookupRoleResponse[]>([]);
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);
  const [allZones, setAllZones] = useState<LookupZoneResponse[]>([]);
  const [filteredZones, setFilteredZones] = useState<LookupZoneResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  // Form state
  const [form, setForm] = useState({
    username: "",
    password: "",
    full_name: "",
    role_id: null as number | null,
    // region_id — asosiy bog'lanish, backendga yuboriladi. zone_id ixtiyoriy.
    region_id: null as number | null,
    zone_id: null as number | null,
    telegram_id: "",
    is_active: true,
  });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadUsers();
    getRolesListApi().then(setRoles);
    getRegionsListApi().then(setRegions);
    getZonesListApi().then(setAllZones);
  }, []);

  async function loadUsers() {
    try {
      const data = await getUsersApi();
      setUsers(data);
    } catch {
      setError("Foydalanuvchilarni yuklashda xatolik");
    } finally {
      setLoading(false);
    }
  }

  // Region o'zgarganda zone larni filter qilish
  const handleRegionChange = async (regionId: number | null) => {
    setForm((prev) => ({ ...prev, region_id: regionId, zone_id: null }));
    if (regionId) {
      try {
        const zones = await getZonesByRegionApi(regionId);
        setFilteredZones(zones);
      } catch {
        setFilteredZones([]);
      }
    } else {
      setFilteredZones([]);
    }
  };

  const openCreate = () => {
    setEditId(null);
    setForm({ username: "", password: "", full_name: "", role_id: null, region_id: null, zone_id: null, telegram_id: "", is_active: true });
    setFilteredZones([]);
    setFormError("");
    setShowModal(true);
  };

  const openEdit = async (user: UserResponse) => {
    setEditId(user.id);
    const matchedRole = roles.find((r) => r.name === user.role);

    // Region — bevosita user.region_id. Eski yozuvda bo'lmasa (region_id hali
    // to'ldirilmagan) zaxira sifatida zonadan aniqlanadi.
    let regionId: number | null = user.region_id ?? null;
    if (!regionId && user.zone_id) {
      const zone = allZones.find((z) => z.id === user.zone_id);
      regionId = zone ? zone.region_id : null;
    }
    if (regionId) {
      // Shu regiondagi zone larni yuklash (cascade dropdown uchun).
      try {
        const zones = await getZonesByRegionApi(regionId);
        setFilteredZones(zones);
      } catch {
        setFilteredZones([]);
      }
    } else {
      setFilteredZones([]);
    }

    setForm({
      username: user.username,
      password: "",
      full_name: user.full_name || "",
      role_id: matchedRole?.id ?? null,
      region_id: regionId,
      zone_id: user.zone_id ?? null,
      telegram_id: user.telegram_id || "",
      is_active: user.is_active,
    });
    setFormError("");
    setShowModal(true);
  };

  async function handleSave() {
    if (!form.username || form.username.length < 3) {
      setFormError("Username kamida 3 belgi bo'lishi kerak");
      return;
    }
    if (!editId && (!form.password || form.password.length < 6)) {
      setFormError("Parol kamida 6 belgi bo'lishi kerak");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      if (editId) {
        const updateData: UpdateUserRequest = {
          username: form.username,
          full_name: form.full_name || undefined,
          role_id: form.role_id,
          region_id: form.region_id,
          zone_id: form.zone_id,
          telegram_id: form.telegram_id || undefined,
          is_active: form.is_active,
        };
        if (form.password) {
          updateData.password = form.password;
        }
        await updateUserApi(editId, updateData);
      } else {
        const createData: CreateUserRequest = {
          username: form.username,
          password: form.password,
          full_name: form.full_name || undefined,
          role_id: form.role_id,
          region_id: form.region_id,
          zone_id: form.zone_id,
          telegram_id: form.telegram_id || undefined,
        };
        await createUserApi(createData);
      }
      setShowModal(false);
      await loadUsers();
    } catch (err: any) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Haqiqatan o'chirmoqchimisiz?")) return;
    try {
      await deleteUserApi(id);
      await loadUsers();
    } catch (err: any) {
      setError(extractErrorMessage(err));
    }
  };

  // Zone nomini topish
  const zoneName = (zoneId: number | null) => {
    if (!zoneId) return "—";
    return allZones.find((z) => z.id === zoneId)?.name || "—";
  };

  // Zone ning regionini topish
  const zoneRegionName = (zoneId: number | null) => {
    if (!zoneId) return "—";
    const zone = allZones.find((z) => z.id === zoneId);
    if (!zone) return "—";
    const region = regions.find((r) => r.id === zone.region_id);
    return region?.name || "—";
  };

  const filtered = useMemo(
    () =>
      users.filter(
        (u) =>
          u.username.toLowerCase().includes(search.toLowerCase()) ||
          (u.full_name || "").toLowerCase().includes(search.toLowerCase())
      ),
    [users, search]
  );

  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [search]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pagedUsers = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  if (loading) return <PageLoader />;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="section-title">Foydalanuvchilar</h2>
          <p className="section-subtitle">Tizim foydalanuvchilari ro'yxati</p>
        </div>
        <PermissionGate permission={PERM.USER_CREATE}>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Yangi foydalanuvchi
          </button>
        </PermissionGate>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-auto underline text-xs">Yopish</button>
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Qidirish (ism yoki username)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field w-full max-w-sm"
        />
      </div>

      {/* Users table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 dark:border-slate-700">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">ID</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Username</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">To'liq ism</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Rol</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Hudud</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Bino</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Telegram</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Holat</th>
              <th className="text-center px-6 py-3 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Amallar</th>
            </tr>
          </thead>
          <tbody>
            {pagedUsers.map((user) => (
              <tr key={user.id} className="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-slate-400">{user.id}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                      <span className="text-xs font-bold text-primary-700 dark:text-primary-400">
                        {(user.full_name || user.username).charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{user.username}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300">{user.full_name || "—"}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    user.role_key === 1
                      ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                      : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  }`}>
                    {user.role || "—"}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300">{user.region_name || zoneRegionName(user.zone_id)}</td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300">{user.zone_name || zoneName(user.zone_id)}</td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-slate-300 font-mono">{user.telegram_id || "—"}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                    user.is_active ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${user.is_active ? "bg-green-500" : "bg-red-500"}`} />
                    {user.is_active ? "Faol" : "Bloklangan"}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <PermissionGate permission={PERM.USER_UPDATE}>
                      <button onClick={() => openEdit(user)} className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300" title="Tahrirlash">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                      </button>
                    </PermissionGate>
                    <PermissionGate permission={PERM.USER_DELETE}>
                      <button onClick={() => handleDelete(user.id)} className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300" title="O'chirish">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      </button>
                    </PermissionGate>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="px-6 py-12 text-center text-gray-400 dark:text-slate-500">Foydalanuvchi topilmadi</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pages={totalPages} onPageChange={setPage} />

      <p className="mt-3 text-xs text-gray-400 dark:text-slate-500">Jami: {filtered.length} ta foydalanuvchi</p>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editId ? "Foydalanuvchini tahrirlash" : "Yangi foydalanuvchi"}
            </h3>

            {formError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">{formError}</div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Username *</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="input-field w-full"
                  placeholder="username"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Parol {editId ? "(bo'sh qoldirsa o'zgarmaydi)" : "*"}
                </label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="input-field w-full"
                  placeholder={editId ? "Yangi parol (ixtiyoriy)" : "Kamida 6 belgi"}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">To'liq ism</label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className="input-field w-full"
                  placeholder="Familiya Ism"
                />
              </div>

              {(() => {
                // Admin (key=1) rolidagi userning rolini faqat super-admin (id=1) o'zgartira oladi.
                // Yangi user yaratishda ham admin biriktirish faqat super-admin huquqi.
                const editingUser = editId ? users.find((u) => u.id === editId) : null;
                const targetIsAdmin = editingUser?.role_key === ADMIN_ROLE_KEY;
                const roleLocked = targetIsAdmin && !isSuperAdmin;
                return (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                      Rol
                    </label>
                    <Md3Select
                      value={form.role_id != null ? String(form.role_id) : ""}
                      onChange={(v) =>
                        setForm({
                          ...form,
                          role_id: v ? Number(v) : null,
                        })
                      }
                      disabled={roleLocked}
                      placeholder="— Tanlanmagan —"
                      options={roles.map((r) => {
                        const isAdminRole = r.key === ADMIN_ROLE_KEY;
                        // Admin variantini super-admin bo'lmaganlar uchun yopiq qilamiz,
                        // lekin agar joriy tanlangan rol shu bo'lsa (edit holatda) — ko'rinib tursin.
                        const optDisabled =
                          isAdminRole && !isSuperAdmin && form.role_id !== r.id;
                        return {
                          value: String(r.id),
                          label: r.name + (optDisabled ? " — faqat super-admin" : ""),
                          disabled: optDisabled,
                        };
                      })}
                    />
                    {roleLocked && (
                      <p className="mt-1.5 text-[11px] text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                        <svg
                          className="w-3.5 h-3.5 mt-px shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 15v2m0-9v4m-9 5h18a2 2 0 001.83-2.82L13.92 4.62a2 2 0 00-3.84 0L2.17 17.18A2 2 0 003 20z"
                          />
                        </svg>
                        Admin rolidagi userning rolini faqat super-admin (id=1)
                        o'zgartira oladi.
                      </p>
                    )}
                  </div>
                );
              })()}

              {/* Cascade: Region → Zone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Hudud</label>
                <Md3Select
                  value={form.region_id != null ? String(form.region_id) : ""}
                  onChange={(v) => handleRegionChange(v ? Number(v) : null)}
                  placeholder="— Tanlanmagan —"
                  options={regions.map((r) => ({ value: String(r.id), label: r.name }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Bino (uy zonasi — ixtiyoriy)</label>
                <Md3Select
                  value={form.zone_id != null ? String(form.zone_id) : ""}
                  onChange={(v) => setForm({ ...form, zone_id: v ? Number(v) : null })}
                  disabled={!form.region_id}
                  placeholder={form.region_id ? "— Tanlang —" : "— Avval hududni tanlang —"}
                  options={filteredZones.map((z) => ({ value: String(z.id), label: z.name }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Telegram ID</label>
                <input
                  type="text"
                  value={form.telegram_id}
                  onChange={(e) => setForm({ ...form, telegram_id: e.target.value })}
                  className="input-field w-full"
                  placeholder="123456789"
                />
              </div>

              {editId && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="rounded"
                  />
                  <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-slate-300">Faol</label>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => { setShowModal(false); setFormError(""); }}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
