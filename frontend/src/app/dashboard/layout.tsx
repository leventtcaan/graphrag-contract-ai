"use client";

/**
 * Dashboard Layout — Korumalı Rota (Protected Route)
 * Token yoksa kullanıcıyı /login'e yönlendirir.
 * Tüm dashboard sayfaları bu layout'u miras alır.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { FileText, LayoutDashboard, LogOut, Shield } from "lucide-react";
import useAuthStore from "@/store/authStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { token, logout } = useAuthStore();

  // Korumalı rota kontrolü: token yoksa login'e yönlendir
  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [token, router]);

  // Token yokken çocuk bileşeni render etme (kısa flash önlemi)
  if (!token) return null;

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* Sol Sidebar */}
      <aside className="flex w-64 flex-shrink-0 flex-col border-r border-slate-800 bg-slate-900">
        {/* Logo alanı */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
            <FileText className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">
            Contract AI
          </span>
        </div>

        {/* Navigasyon menüsü */}
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          <NavItem
            icon={<LayoutDashboard className="h-4 w-4" />}
            label="Sözleşmeler"
            active
          />
          <NavItem
            icon={<Shield className="h-4 w-4" />}
            label="Uyum Raporu"
            disabled
          />
        </nav>

        {/* Çıkış butonu — sidebar'ın en altında */}
        <div className="border-t border-slate-800 p-3">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-red-400"
          >
            <LogOut className="h-4 w-4" />
            Çıkış Yap
          </button>
        </div>
      </aside>

      {/* Ana içerik alanı */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Üst başlık çubuğu */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900 px-6">
          <h1 className="text-sm font-medium text-slate-300">Dashboard</h1>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-xs text-slate-500">Bağlı</span>
          </div>
        </header>

        {/* Sayfa içeriği */}
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </main>
    </div>
  );
}

// ─── Yardımcı bileşenler ───────────────────────────────────────────────────

function NavItem({
  icon,
  label,
  active = false,
  disabled = false,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      disabled={disabled}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
        active
          ? "bg-indigo-600/15 text-indigo-400"
          : disabled
            ? "cursor-not-allowed text-slate-600"
            : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
