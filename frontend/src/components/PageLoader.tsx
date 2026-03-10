export default function PageLoader({ text = "Yuklanmoqda..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
      <div className="relative">
        <div className="w-12 h-12 rounded-full border-[3px] border-primary-200 dark:border-primary-900/40" />
        <div className="absolute inset-0 w-12 h-12 rounded-full border-[3px] border-transparent border-t-primary-600 animate-spin" />
      </div>
      <p className="text-sm text-gray-400 dark:text-slate-500 animate-pulse">{text}</p>
    </div>
  );
}
