interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: "primary" | "green" | "purple" | "orange";
}

const iconBg: Record<string, string> = {
  primary: "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400",
  green: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400",
  purple: "bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400",
  orange: "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400",
};

const valueColors: Record<string, string> = {
  primary: "text-primary-700 dark:text-primary-300",
  green: "text-emerald-700 dark:text-emerald-300",
  purple: "text-violet-700 dark:text-violet-300",
  orange: "text-amber-700 dark:text-amber-300",
};

export default function StatsCard({
  title,
  value,
  subtitle,
  icon,
  color = "primary",
}: StatsCardProps) {
  return (
    <div className="glass-card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[12px] sm:text-sm text-gray-500 dark:text-slate-400 font-medium truncate">
            {title}
          </p>
          <p className={`text-2xl sm:text-3xl font-bold mt-1.5 sm:mt-2 ${valueColors[color]} tabular-nums`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-[11px] sm:text-xs text-gray-400 dark:text-slate-500 mt-1.5 line-clamp-2">
              {subtitle}
            </p>
          )}
        </div>
        {icon && (
          <div
            className={`w-10 h-10 sm:w-11 sm:h-11 rounded-2xl flex items-center justify-center shrink-0 ${iconBg[color]}`}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
