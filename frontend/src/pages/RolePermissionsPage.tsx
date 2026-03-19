import { useCallback, useEffect, useState, useRef } from "react";
import type { PermissionResponse, RolePermissionsResponse } from "../interfaces";
import {
  assignPermissionsToRoleApi,
  getPermissionsApi,
  getRolesWithPermissionsApi,
} from "../api";

/* ── Material-inspired icon components ── */
function ShieldIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}

function CheckCircleIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function SaveIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
    </svg>
  );
}

/* ── Grouped icon map for permission groups ── */
const groupIcons: Record<string, string> = {};
const groupColors: string[] = [
  "from-blue-500 to-blue-600",
  "from-emerald-500 to-emerald-600",
  "from-violet-500 to-violet-600",
  "from-amber-500 to-amber-600",
  "from-rose-500 to-rose-600",
  "from-cyan-500 to-cyan-600",
  "from-indigo-500 to-indigo-600",
  "from-teal-500 to-teal-600",
];

const groupBgColors: string[] = [
  "bg-blue-50 dark:bg-blue-900/15 border-blue-100 dark:border-blue-800/30",
  "bg-emerald-50 dark:bg-emerald-900/15 border-emerald-100 dark:border-emerald-800/30",
  "bg-violet-50 dark:bg-violet-900/15 border-violet-100 dark:border-violet-800/30",
  "bg-amber-50 dark:bg-amber-900/15 border-amber-100 dark:border-amber-800/30",
  "bg-rose-50 dark:bg-rose-900/15 border-rose-100 dark:border-rose-800/30",
  "bg-cyan-50 dark:bg-cyan-900/15 border-cyan-100 dark:border-cyan-800/30",
  "bg-indigo-50 dark:bg-indigo-900/15 border-indigo-100 dark:border-indigo-800/30",
  "bg-teal-50 dark:bg-teal-900/15 border-teal-100 dark:border-teal-800/30",
];

const groupTextColors: string[] = [
  "text-blue-700 dark:text-blue-300",
  "text-emerald-700 dark:text-emerald-300",
  "text-violet-700 dark:text-violet-300",
  "text-amber-700 dark:text-amber-300",
  "text-rose-700 dark:text-rose-300",
  "text-cyan-700 dark:text-cyan-300",
  "text-indigo-700 dark:text-indigo-300",
  "text-teal-700 dark:text-teal-300",
];

/* ── Custom toggle switch ── */
function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      className={`
        relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full
        transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:ring-offset-2 dark:focus:ring-offset-slate-800
        ${checked ? "bg-primary-600" : "bg-gray-300 dark:bg-slate-600"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <span
        className={`
          pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-md ring-0
          transition-transform duration-200 ease-in-out mt-0.5
          ${checked ? "translate-x-4 ml-0.5" : "translate-x-0 ml-0.5"}
        `}
      />
    </button>
  );
}

/* ── Snackbar notification ── */
function Snackbar({ msg, onClose }: { msg: { type: "ok" | "err"; text: string }; onClose: () => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    timerRef.current = setTimeout(onClose, 3000);
    return () => clearTimeout(timerRef.current);
  }, [onClose]);

  return (
    <div className={`
      fixed bottom-6 left-1/2 -translate-x-1/2 z-50
      flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl
      animate-slide-up
      ${msg.type === "ok"
        ? "bg-emerald-600 text-white"
        : "bg-red-600 text-white"
      }
    `}>
      {msg.type === "ok" ? (
        <CheckCircleIcon className="w-5 h-5 flex-shrink-0" />
      ) : (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )}
      <span className="text-sm font-medium">{msg.text}</span>
      <button onClick={onClose} className="ml-2 hover:opacity-70 transition-opacity">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export default function RolePermissionsPage() {
  const [roles, setRoles] = useState<RolePermissionsResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalIds, setOriginalIds] = useState<Set<number>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [rolesData, permsData] = await Promise.all([
        getRolesWithPermissionsApi(),
        getPermissionsApi(),
      ]);
      setRoles(rolesData);
      setPermissions(permsData);
      if (rolesData.length > 0 && selectedRoleId === null) {
        const first = rolesData[0];
        setSelectedRoleId(first.id);
        const ids = new Set(first.permissions.map((p) => p.id));
        setCheckedIds(ids);
        setOriginalIds(new Set(ids));
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

  // Track changes
  useEffect(() => {
    if (originalIds.size === 0 && checkedIds.size === 0) {
      setHasChanges(false);
      return;
    }
    const changed = originalIds.size !== checkedIds.size ||
      [...checkedIds].some(id => !originalIds.has(id));
    setHasChanges(changed);
  }, [checkedIds, originalIds]);

  const selectRole = (roleId: number) => {
    setSelectedRoleId(roleId);
    const role = roles.find((r) => r.id === roleId);
    if (role) {
      const ids = new Set(role.permissions.map((p) => p.id));
      setCheckedIds(ids);
      setOriginalIds(new Set(ids));
    }
    setMsg(null);
    setHasChanges(false);
  };

  const togglePermission = (permId: number) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(permId)) next.delete(permId);
      else next.add(permId);
      return next;
    });
  };

  const toggleGroup = (groupPerms: PermissionResponse[]) => {
    const allChecked = groupPerms.every((p) => checkedIds.has(p.id));
    setCheckedIds((prev) => {
      const next = new Set(prev);
      groupPerms.forEach((p) => {
        if (allChecked) next.delete(p.id);
        else next.add(p.id);
      });
      return next;
    });
  };

  const handleSave = async () => {
    if (!selectedRoleId) return;
    setSaving(true);
    setMsg(null);
    try {
      const updated = await assignPermissionsToRoleApi(selectedRoleId, {
        permission_ids: Array.from(checkedIds),
      });
      setRoles((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      const ids = new Set(updated.permissions.map((p) => p.id));
      setOriginalIds(ids);
      setCheckedIds(new Set(ids));
      setMsg({ type: "ok", text: "Muvaffaqiyatli saqlandi!" });
      setHasChanges(false);
    } catch {
      setMsg({ type: "err", text: "Saqlashda xatolik yuz berdi" });
    } finally {
      setSaving(false);
    }
  };

  // Group permissions
  const grouped: Record<string, PermissionResponse[]> = {};
  permissions.forEach((p) => {
    if (!grouped[p.group]) grouped[p.group] = [];
    grouped[p.group].push(p);
  });

  const selectedRole = roles.find((r) => r.id === selectedRoleId);
  const groupKeys = Object.keys(grouped);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="relative">
          <div className="w-12 h-12 rounded-full border-4 border-primary-100 dark:border-primary-900/30" />
          <div className="absolute inset-0 w-12 h-12 rounded-full border-4 border-transparent border-t-primary-600 animate-spin" />
        </div>
        <p className="text-sm text-gray-400 dark:text-slate-500">Yuklanmoqda...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/20">
            <ShieldIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="section-title">Huquqlarni boshqarish</h1>
            <p className="section-subtitle">Har bir rolga permissionlarni tayinlash va boshqarish</p>
          </div>
        </div>
        {/* Summary chip */}
        {selectedRole && selectedRole.key !== 1 && (
          <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-full bg-primary-50 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-800/30">
            <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
            <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
              {checkedIds.size}/{permissions.length} ta huquq tanlangan
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-6">
        {/* ── Roles sidebar ── */}
        <div className="w-72 flex-shrink-0">
          <div className="glass-card overflow-hidden sticky top-4">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-slate-500">
                Rollar
              </h3>
            </div>
            <div className="p-2">
              {roles.map((role) => {
                const isActive = selectedRoleId === role.id;
                return (
                  <button
                    key={role.id}
                    onClick={() => selectRole(role.id)}
                    className={`
                      w-full text-left px-4 py-3.5 rounded-xl mb-1 last:mb-0
                      transition-all duration-200 group relative
                      ${isActive
                        ? "bg-primary-600 text-white shadow-lg shadow-primary-500/25"
                        : "hover:bg-gray-50 dark:hover:bg-slate-700/50 text-gray-700 dark:text-slate-300"
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`
                        w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0
                        transition-colors duration-200
                        ${isActive
                          ? "bg-white/20"
                          : "bg-primary-50 dark:bg-primary-900/20"
                        }
                      `}>
                        <ShieldIcon className={`w-4.5 h-4.5 ${isActive ? "text-white" : "text-primary-600 dark:text-primary-400"}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm truncate">{role.name}</div>
                        <div className={`text-xs mt-0.5 flex items-center gap-1.5 ${isActive ? "text-primary-100" : "text-gray-400 dark:text-slate-500"}`}>
                          <span className="font-mono">key={role.key}</span>
                          <span>&middot;</span>
                          <span>{role.permissions.length} ta huquq</span>
                        </div>
                      </div>
                      {isActive && (
                        <div className="w-1.5 h-8 bg-white/40 rounded-full flex-shrink-0" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Permissions area ── */}
        <div className="flex-1 min-w-0">
          {selectedRole && selectedRole.key === 1 ? (
            /* Admin full-access banner */
            <div className="glass-card overflow-hidden">
              <div className="relative px-8 py-12 text-center">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/10 dark:to-orange-900/10" />
                <div className="relative">
                  <div className="w-20 h-20 mx-auto mb-5 rounded-3xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-xl shadow-amber-500/20">
                    <ShieldIcon className="w-10 h-10 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                    Admin — to'liq huquqlar
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-slate-400 max-w-md mx-auto">
                    Admin roli (key=1) avtomatik ravishda barcha permissionlardan o'tadi.
                    Bu rolning huquqlarini cheklash mumkin emas.
                  </p>
                  <div className="flex items-center justify-center gap-2 mt-5">
                    <div className="flex -space-x-1">
                      {[...Array(Math.min(permissions.length, 5))].map((_, i) => (
                        <div key={i} className="w-6 h-6 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 border-2 border-white dark:border-slate-800 flex items-center justify-center">
                          <CheckCircleIcon className="w-3 h-3 text-white" />
                        </div>
                      ))}
                    </div>
                    <span className="text-xs font-medium text-amber-700 dark:text-amber-400 ml-1">
                      {permissions.length} ta huquqning barchasi faol
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {groupKeys.map((group, gi) => {
                const perms = grouped[group];
                const colorIdx = gi % groupColors.length;
                const allChecked = perms.every((p) => checkedIds.has(p.id));
                const someChecked = perms.some((p) => checkedIds.has(p.id)) && !allChecked;
                const checkedCount = perms.filter((p) => checkedIds.has(p.id)).length;

                return (
                  <div
                    key={group}
                    className="glass-card overflow-hidden transition-all duration-200 hover:shadow-card-hover"
                    style={{ animationDelay: `${gi * 0.05}s` }}
                  >
                    {/* Group header */}
                    <div className="flex items-center gap-4 px-5 py-4 border-b border-gray-100 dark:border-slate-700/50">
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${groupColors[colorIdx]} flex items-center justify-center shadow-sm flex-shrink-0`}>
                        <span className="text-white text-sm font-bold">{group.charAt(0).toUpperCase()}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-bold text-gray-800 dark:text-slate-200">{group}</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          {/* Progress bar */}
                          <div className="flex-1 max-w-[120px] h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full bg-gradient-to-r ${groupColors[colorIdx]} transition-all duration-300`}
                              style={{ width: `${(checkedCount / perms.length) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-400 dark:text-slate-500">
                            {checkedCount}/{perms.length}
                          </span>
                        </div>
                      </div>
                      {/* Select all toggle */}
                      <div className="flex items-center gap-2.5">
                        <span className="text-xs text-gray-400 dark:text-slate-500 hidden sm:inline">
                          {allChecked ? "Barchasi" : someChecked ? "Qisman" : "Hech biri"}
                        </span>
                        <button
                          onClick={() => toggleGroup(perms)}
                          className={`
                            px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200
                            ${allChecked
                              ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/40"
                              : "bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600"
                            }
                          `}
                        >
                          {allChecked ? "Bekor qilish" : "Hammasini"}
                        </button>
                      </div>
                    </div>

                    {/* Permissions grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-4">
                      {perms.map((perm) => {
                        const isChecked = checkedIds.has(perm.id);
                        return (
                          <label
                            key={perm.id}
                            className={`
                              flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer
                              transition-all duration-200 border
                              ${isChecked
                                ? `${groupBgColors[colorIdx]}`
                                : "border-transparent hover:bg-gray-50 dark:hover:bg-slate-700/30 hover:border-gray-100 dark:hover:border-slate-700"
                              }
                            `}
                          >
                            <ToggleSwitch
                              checked={isChecked}
                              onChange={() => togglePermission(perm.id)}
                            />
                            <div className="flex-1 min-w-0">
                              <div className={`text-sm font-medium transition-colors ${isChecked ? groupTextColors[colorIdx] : "text-gray-700 dark:text-slate-300"}`}>
                                {perm.name}
                              </div>
                              <div className="text-[11px] text-gray-400 dark:text-slate-500 font-mono truncate mt-0.5">
                                {perm.codename}
                              </div>
                            </div>
                            {isChecked && (
                              <CheckCircleIcon className={`w-4 h-4 flex-shrink-0 ${groupTextColors[colorIdx]} opacity-60`} />
                            )}
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}

              {/* ── Sticky save bar ── */}
              <div className={`
                sticky bottom-4 z-10
                transition-all duration-300 ease-out
                ${hasChanges ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"}
              `}>
                <div className="glass-card !rounded-2xl px-6 py-4 flex items-center justify-between shadow-2xl border-primary-200 dark:border-primary-800/40">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                      O'zgarishlar saqlanmagan
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => {
                        setCheckedIds(new Set(originalIds));
                        setHasChanges(false);
                      }}
                      className="btn-secondary !py-2 !px-4 !text-sm"
                    >
                      Bekor qilish
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="btn-primary !py-2 !px-5 !text-sm flex items-center gap-2"
                    >
                      {saving ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Saqlanmoqda...
                        </>
                      ) : (
                        <>
                          <SaveIcon className="w-4 h-4" />
                          Saqlash
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Snackbar notification */}
      {msg && <Snackbar msg={msg} onClose={() => setMsg(null)} />}
    </div>
  );
}
