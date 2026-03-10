interface PaginationProps {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, pages, onPageChange }: PaginationProps) {
  if (pages <= 1) return null;

  const getPageNumbers = () => {
    const nums: (number | "...")[] = [];
    if (pages <= 7) {
      for (let i = 1; i <= pages; i++) nums.push(i);
    } else {
      nums.push(1);
      if (page > 3) nums.push("...");
      for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) {
        nums.push(i);
      }
      if (page < pages - 2) nums.push("...");
      nums.push(pages);
    }
    return nums;
  };

  return (
    <div className="flex items-center justify-center gap-1.5 mt-6">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3.5 py-2 text-sm rounded-xl border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-slate-700 transition"
      >
        Oldingi
      </button>
      {getPageNumbers().map((num, i) =>
        num === "..." ? (
          <span key={`dots-${i}`} className="px-2 text-gray-400 dark:text-slate-500">...</span>
        ) : (
          <button
            key={num}
            onClick={() => onPageChange(num)}
            className={`w-10 h-10 text-sm rounded-xl border transition-all duration-200 ${
              num === page
                ? "bg-primary-600 text-white border-primary-600 shadow-md shadow-primary-600/25"
                : "border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700"
            }`}
          >
            {num}
          </button>
        )
      )}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= pages}
        className="px-3.5 py-2 text-sm rounded-xl border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-slate-700 transition"
      >
        Keyingi
      </button>
    </div>
  );
}
