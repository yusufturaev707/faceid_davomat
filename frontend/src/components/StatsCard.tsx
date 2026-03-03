interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: "blue" | "green" | "purple" | "orange";
}

const colors = {
  blue: "bg-blue-50 text-blue-700",
  green: "bg-green-50 text-green-700",
  purple: "bg-purple-50 text-purple-700",
  orange: "bg-orange-50 text-orange-700",
};

export default function StatsCard({ title, value, subtitle, color = "blue" }: StatsCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${colors[color].split(" ")[1]}`}>{value}</p>
      {subtitle && <p className={`text-xs mt-2 px-2 py-1 rounded-full inline-block ${colors[color]}`}>{subtitle}</p>}
    </div>
  );
}
