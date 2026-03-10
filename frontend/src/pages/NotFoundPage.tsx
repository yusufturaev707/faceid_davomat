import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "rgb(var(--color-bg))" }}>
      <div className="text-center">
        <h1 className="text-8xl font-bold text-gray-200 dark:text-slate-700 mb-4">404</h1>
        <p className="text-xl text-gray-600 dark:text-slate-400 mb-2">Sahifa topilmadi</p>
        <p className="text-sm text-gray-400 dark:text-slate-500 mb-8">Kechirasiz, siz qidirayotgan sahifa mavjud emas</p>
        <Link to="/" className="btn-primary inline-block">Bosh sahifaga qaytish</Link>
      </div>
    </div>
  );
}
