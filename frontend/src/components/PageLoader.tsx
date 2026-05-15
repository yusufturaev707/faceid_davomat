export default function PageLoader({ text = "Yuklanmoqda..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] sm:min-h-[60vh] gap-4 px-4 text-center">
      <div className="relative">
        <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-full border-[3px] border-primary-200 dark:border-primary-900/40" />
        <div className="absolute inset-0 rounded-full border-[3px] border-transparent border-t-primary-600 animate-spin" />
      </div>
      <p className="text-sm text-gray-500 dark:text-slate-400 animate-pulse">
        {text}
      </p>
    </div>
  );
}
