"use client";

/**
 * Giriş Sayfası
 * FastAPI OAuth2 endpoint'i application/x-www-form-urlencoded bekliyor,
 * bu yüzden axios ile FormData (URLSearchParams) gönderiyoruz.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Lock, Mail, Loader2 } from "lucide-react";
import api from "@/lib/api";
import useAuthStore from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // FastAPI OAuth2 endpoint'i form-urlencoded formatı bekliyor
      const params = new URLSearchParams();
      params.append("username", email); // FastAPI field adı "username"
      params.append("password", password);

      const { data } = await api.post<{ access_token: string }>(
        "/auth/login/access-token",
        params,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );

      // Token'ı Zustand store'a kaydet (localStorage'a da persist edilir)
      setToken(data.access_token);
      router.push("/dashboard");
    } catch (err: unknown) {
      // Hata mesajını kullanıcıya göster
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Giriş başarısız. E-posta veya şifrenizi kontrol edin.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      {/* Arka plan dekor noktaları */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-violet-600/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo ve başlık */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-600/30">
            <FileText className="h-7 w-7 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              GraphRAG Contract AI
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              IT uyum ve sözleşme analiz platformu
            </p>
          </div>
        </div>

        {/* Form kartı */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-sm">
          <h2 className="mb-6 text-lg font-semibold text-white">
            Hesabınıza giriş yapın
          </h2>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* E-posta alanı */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="email"
                className="text-sm font-medium text-slate-300"
              >
                E-posta
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ornek@hukukburosu.com"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Şifre alanı */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="password"
                className="text-sm font-medium text-slate-300"
              >
                Şifre
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Hata mesajı */}
            {error && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                {error}
              </p>
            )}

            {/* Giriş butonu */}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Giriş yapılıyor…
                </>
              ) : (
                "Giriş Yap"
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-slate-600">
          © 2026 GraphRAG Contract AI · Tüm hakları saklıdır
        </p>
      </div>
    </div>
  );
}
