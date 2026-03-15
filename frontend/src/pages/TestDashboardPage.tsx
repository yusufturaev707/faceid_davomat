import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { TestSessionResponse, TestSessionListResponse } from "../interfaces";
import { getTestSessionsApi } from "../api";
import PageLoader from "../components/PageLoader";

export default function TestDashboardPage() {
  const [data, setData] = useState<TestSessionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getTestSessionsApi({ page: 1, per_page: 100 })
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;

  const sessions = data?.items || [];
  const totalSessions = sessions.length;
  const activeSessions = sessions.filter((s) => s.is_active).length;
  const totalStudents = sessions.reduce((sum, s) => sum + s.count_total_student, 0);
  const totalSmenas = sessions.reduce((sum, s) => sum + s.smenas.length, 0);

  // Sessiyalarni state bo'yicha guruhlash
  const stateGroups: Record<string, TestSessionResponse[]> = {};
  sessions.forEach((s) => {
    const stateName = s.test_state?.name || "Noma'lum";
    if (!stateGroups[stateName]) stateGroups[stateName] = [];
    stateGroups[stateName].push(s);
  });

  // Kunlik taqsimot (yaqin 14 kun)
  const today = new Date();
  const upcomingSessions = sessions.filter((s) => {
    const finish = new Date(s.finish_date);
    return finish >= today && s.is_active;
  });

  return (
    <div>
      <div className="mb-8">
        <h2 className="section-title">Test Dashboard</h2>
        <p className="section-subtitle">Test sessiyalari umumiy statistikasi</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Jami sessiyalar"
          value={totalSessions}
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          }
          color="primary"
        />
        <StatCard
          title="Faol sessiyalar"
          value={activeSessions}
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          color="green"
        />
        <StatCard
          title="Jami talabalar"
          value={totalStudents}
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          }
          color="purple"
        />
        <StatCard
          title="Jami smenalar"
          value={totalSmenas}
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          color="orange"
        />
      </div>

      {/* Holat bo'yicha taqsimot */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-4">
            Holat bo'yicha taqsimot
          </h3>
          {Object.keys(stateGroups).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stateGroups).map(([state, items]) => {
                const pct = totalSessions > 0 ? (items.length / totalSessions) * 100 : 0;
                return (
                  <div key={state}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-gray-600 dark:text-slate-400">{state}</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {items.length}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-primary-500 h-2 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-slate-500">Ma'lumot yo'q</p>
          )}
        </div>

        {/* Yaqinlashayotgan sessiyalar */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-4">
            Faol va kelayotgan sessiyalar
          </h3>
          {upcomingSessions.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {upcomingSessions.slice(0, 10).map((s) => (
                <div
                  key={s.id}
                  onClick={() => navigate("/test-sessions")}
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {s.name}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      {s.test?.name} · {s.smenas.length} smena
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-medium text-gray-600 dark:text-slate-300">
                      {s.start_date}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      {s.finish_date}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-slate-500">
              Faol sessiya yo'q
            </p>
          )}
        </div>
      </div>

      {/* Oxirgi sessiyalar */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
            Oxirgi sessiyalar
          </h3>
          <button
            onClick={() => navigate("/test-sessions")}
            className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
          >
            Barchasini ko'rish →
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 dark:border-slate-700">
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  #
                </th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  Nomi
                </th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  Test
                </th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  Holat
                </th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  Smenalar
                </th>
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase">
                  Sana
                </th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 5).map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors"
                >
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400">
                    {s.number}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                    {s.name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-slate-300">
                    {s.test?.name || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                      {s.test_state?.name || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-slate-300">
                    {s.smenas.length}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-slate-400">
                    {s.start_date} — {s.finish_date}
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400 dark:text-slate-500 text-sm">
                    Sessiya yo'q
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: "primary" | "green" | "purple" | "orange";
}) {
  const colorMap = {
    primary: "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400",
    green: "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400",
    purple: "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400",
    orange: "bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400",
  };

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorMap[color]}`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value.toLocaleString()}</p>
      <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{title}</p>
    </div>
  );
}
