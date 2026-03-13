"use client";

/**
 * Dashboard Layout — Korumalı Rota + Mobil Hamburger Menü
 * Token yoksa /login'e yönlendirir.
 * lg ve üzeri → sabit sidebar | md ve altı → slide-in drawer
 */

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  FileText,
  LayoutDashboard,
  LogOut,
  Shield,
  Menu,
  X,
} from "lucide-react";
import useAuthStore from "@/store/authStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, logout } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!token) router.replace("/login");
  }, [token, router]);

  // Rota değişince mobil menüyü kapat
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (!token) return null;

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  const isContractsActive =
    pathname === "/dashboard" ||
    (pathname.startsWith("/dashboard/contracts") &&
      !pathname.includes("/compliance"));
  const isComplianceActive =
    pathname.startsWith("/dashboard/compliance") ||
    pathname.includes("/compliance");

  const navItems = [
    {
      icon: <LayoutDashboard className="h-4 w-4" />,
      label: "Sözleşmeler",
      active: isContractsActive,
      onClick: () => router.push("/dashboard"),
    },
    {
      icon: <Shield className="h-4 w-4" />,
      label: "Uyum Raporu",
      active: isComplianceActive,
      onClick: () => router.push("/dashboard/compliance"),
    },
  ];

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* Mobil backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sol Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-shrink-0 flex-col border-r border-slate-800 bg-slate-900 transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 shadow-lg shadow-indigo-600/30">
            <FileText className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">Contract AI</span>
        </div>

        {/* Navigasyon */}
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          {navItems.map((item) => (
            <NavItem key={item.label} {...item} />
          ))}
        </nav>

        {/* Çıkış */}
        <div className="border-t border-slate-800 p-3">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-red-400 active:scale-[0.98]"
          >
            <LogOut className="h-4 w-4" />
            Çıkış Yap
          </button>
        </div>
      </aside>

      {/* Ana içerik */}
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Üst başlık */}
        <header className="flex h-16 flex-shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900 px-4 lg:px-6">
          <div className="flex items-center gap-3">
            {/* Hamburger — yalnızca mobilde */}
            <button
              onClick={() => setMobileOpen((v) => !v)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-200 active:scale-95 lg:hidden"
              aria-label="Menüyü aç/kapat"
            >
              {mobileOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
            <h1 className="text-sm font-medium text-slate-300">Dashboard</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-40" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs text-slate-500">Bağlı</span>
          </div>
        </header>

        {/* Sayfa içeriği */}
        <div className="flex-1 overflow-auto p-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 active:scale-[0.98] ${
        active
          ? "bg-indigo-600/15 text-indigo-400 shadow-sm"
          : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
      }`}
    >
      <span
        className={`flex-shrink-0 transition-transform duration-200 ${
          !active ? "group-hover:scale-110" : ""
        }`}
      >
        {icon}
      </span>
      {label}
      {active && (
        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-400" />
      )}
    </button>
  );
}
