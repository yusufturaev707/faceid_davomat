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

  const navBtnBase =
    "inline-flex items-center justify-center h-10 px-3 sm:px-4 text-sm rounded-full border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-slate-700/60 transition-colors";

  return (
    <div className="flex items-center justify-center flex-wrap gap-1.5 mt-6">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className={navBtnBase}
        aria-label="Oldingi sahifa"
      >
        <svg
          className="w-4 h-4 sm:mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        <span className="hidden sm:inline">Oldingi</span>
      </button>

      <div className="flex items-center gap-1">
        {getPageNumbers().map((num, i) =>
          num === "..." ? (
            <span
              key={`dots-${i}`}
              className="px-2 text-gray-400 dark:text-slate-500"
            >
              ...
            </span>
          ) : (
            <button
              key={num}
              onClick={() => onPageChange(num)}
              aria-current={num === page ? "page" : undefined}
              className={`w-10 h-10 text-sm rounded-full transition-colors ${
                num === page
                  ? "bg-primary-600 text-white shadow-sm shadow-primary-600/30 font-semibold"
                  : "text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700/60"
              }`}
            >
              {num}
            </button>
          )
        )}
      </div>

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= pages}
        className={navBtnBase}
        aria-label="Keyingi sahifa"
      >
        <span className="hidden sm:inline">Keyingi</span>
        <svg
          className="w-4 h-4 sm:ml-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>
    </div>
  );
}
