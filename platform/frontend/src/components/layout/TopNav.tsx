import Link from "next/link";
import { PersonaSwitcher } from "@/components/layout/PersonaSwitcher";

export function TopNav() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 w-full border-b bg-white shadow-sm">
      <div className="flex h-full items-center justify-between px-6">
        <Link
          href="/"
          className="text-xl font-bold tracking-tight text-slate-900 hover:text-slate-700 transition-colors"
        >
          APEX
        </Link>
        <PersonaSwitcher />
      </div>
    </header>
  );
}
