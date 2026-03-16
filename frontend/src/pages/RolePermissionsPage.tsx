import { useCallback, useEffect, useState } from "react";
import type { PermissionResponse, RolePermissionsResponse } from "../interfaces";
import {
  assignPermissionsToRoleApi,
  getPermissionsApi,
  getRolesWithPermissionsApi,
} from "../api";

export default function RolePermissionsPage() {
  const [roles, setRoles] = useState<RolePermissionsResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [rolesData, permsData] = await Promise.all([
        getRolesWithPermissionsApi(),
        getPermissionsApi(),
      ]);
      setRoles(rolesData);
      setPermissions(permsData);
      // Auto-select first role
      if (rolesData.length > 0 && selectedRoleId === null) {
        const first = rolesData[0];
        setSelectedRoleId(first.id);
        setCheckedIds(new Set(first.permissions.map((p) => p.id)));
      }
    } catch {
      setMsg({ type: "err", text: "Ma'lumotlarni yuklashda xatolik" });
    } finally {
      setLoading(false);
    }
  }, [selectedRoleId]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rolni tanlash
  const selectRole = (roleId: number) => {
    setSelectedRoleId(roleId);
    const role = roles.find((r) => r.id === roleId);
    if (role) {
      setCheckedIds(new Set(role.permissions.map((p) => p.id)));
    }
    setMsg(null);
  };

  // Permission toggle
  const togglePermission = (permId: number) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(permId)) {
        next.delete(permId);
      } else {
        next.add(permId);
      }
      return next;
    });
  };

  // Guruhdagi barcha permissionlarni toggle qilish
  const toggleGroup = (groupPerms: PermissionResponse[]) => {
    const allChecked = groupPerms.every((p) => checkedIds.has(p.id));
    setCheckedIds((prev) => {
      const next = new Set(prev);
      groupPerms.forEach((p) => {
        if (allChecked) {
          next.delete(p.id);
        } else {
          next.add(p.id);
        }
      });
      return next;
    });
  };

  // Saqlash
  const handleSave = async () => {
    if (!selectedRoleId) return;
    setSaving(true);
    setMsg(null);
    try {
      const updated = await assignPermissionsToRoleApi(selectedRoleId, {
        permission_ids: Array.from(checkedIds),
      });
      // Update local state
      setRoles((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setMsg({ type: "ok", text: "Muvaffaqiyatli saqlandi!" });
    } catch {
      setMsg({ type: "err", text: "Saqlashda xatolik yuz berdi" });
    } finally {
      setSaving(false);
    }
  };

  // Group permissions by group field
  const grouped: Record<string, PermissionResponse[]> = {};
  permissions.forEach((p) => {
    if (!grouped[p.group]) grouped[p.group] = [];
    grouped[p.group].push(p);
  });

  const selectedRole = roles.find((r) => r.id === selectedRoleId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Rol huquqlari boshqaruvi
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
          Har bir rolga permissionlarni tayinlash va boshqarish
        </p>
      </div>

      <div className="flex gap-6">
        {/* Roles list (sidebar) */}
        <div className="w-64 flex-shrink-0">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
                Rollar
              </h3>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-slate-700">
              {roles.map((role) => (
                <button
                  key={role.id}
                  onClick={() => selectRole(role.id)}
                  className={`w-full text-left px-4 py-3 transition-colors ${
                    selectedRoleId === role.id
                      ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
                      : "hover:bg-gray-50 dark:hover:bg-slate-700/50 text-gray-700 dark:text-slate-300"
                  }`}
                >
                  <div className="font-medium text-sm">{role.name}</div>
                  <div className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">
                    key={role.key} &middot; {role.permissions.length} ta huquq
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Permissions grid */}
        <div className="flex-1">
          {selectedRole && selectedRole.key === 1 ? (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6 text-center">
              <svg
                className="w-12 h-12 mx-auto text-amber-500 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              <p className="text-amber-800 dark:text-amber-200 font-medium">
                Admin roli barcha huquqlarga ega
              </p>
              <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
                Admin (key=1) avtomatik ravishda barcha permissionlardan o'tadi
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(grouped).map(([group, perms]) => {
                const allChecked = perms.every((p) => checkedIds.has(p.id));
                const someChecked =
                  perms.some((p) => checkedIds.has(p.id)) && !allChecked;

                return (
                  <div
                    key={group}
                    className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700"
                  >
                    {/* Group header */}
                    <div className="px-4 py-3 border-b border-gray-100 dark:border-slate-700 flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={allChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = someChecked;
                        }}
                        onChange={() => toggleGroup(perms)}
                        className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm font-semibold text-gray-700 dark:text-slate-300">
                        {group}
                      </span>
                      <span className="text-xs text-gray-400 dark:text-slate-500">
                        ({perms.filter((p) => checkedIds.has(p.id)).length}/
                        {perms.length})
                      </span>
                    </div>
                    {/* Permissions in group */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 p-3">
                      {perms.map((perm) => (
                        <label
                          key={perm.id}
                          className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/30 cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={checkedIds.has(perm.id)}
                            onChange={() => togglePermission(perm.id)}
                            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <div>
                            <div className="text-sm text-gray-700 dark:text-slate-300">
                              {perm.name}
                            </div>
                            <div className="text-xs text-gray-400 dark:text-slate-500 font-mono">
                              {perm.codename}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}

              {/* Save button */}
              <div className="flex items-center gap-4">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-6 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                  {saving ? "Saqlanmoqda..." : "Saqlash"}
                </button>
                {msg && (
                  <span
                    className={`text-sm font-medium ${
                      msg.type === "ok"
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {msg.text}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
