"use client";

/**
 * Uyum Genel Durum Sayfası — /dashboard/compliance
 *
 * Tüm sözleşmeleri listeler; analiz edilmiş olanlar için
 * bireysel uyum raporuna doğrudan erişim sağlar.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  Archive,
  ChevronRight,
  Lock,
} from "lucide-react";
import api from "@/lib/api";

type ContractStatus =
  | "uploaded"
  | "processing"
  | "analyzed"
  | "failed"
  | "archived";

interface Contract {
  id: string;
  title: string;
  status: ContractStatus;
  created_at: string;
  original_filename: string | null;
}

const STATUS_CONFIG: Record<
  ContractStatus,
  { label: string; color: string; icon: React.ReactNode }
> = {
  uploaded: {
    label: "Yüklendi",
    color: "text-amber-400 bg-amber-400/10 border-amber-400/20",
    icon: <Clock className="h-3.5 w-3.5" />,
  },
  processing: {
    label: "İşleniyor",
    color: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
  },
  analyzed: {
    label: "Analiz Edildi",
    color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
  },
  failed: {
    label: "Hata",
    color: "text-red-400 bg-red-400/10 border-red-400/20",
    icon: <AlertCircle className="h-3.5 w-3.5" />,
  },
  archived: {
    label: "Arşivlendi",
    color: "text-slate-400 bg-slate-400/10 border-slate-400/20",
    icon: <Archive className="h-3.5 w-3.5" />,
  },
};

export default function ComplianceOverviewPage() {
  const router = useRouter();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<{ items: Contract[]; total: number }>(
        "/contracts/"
      );
      setContracts(data.items);
    } catch {
      setError("Sözleşmeler yüklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  const analyzed = contracts.filter((c) => c.status === "analyzed");
  const others = contracts.filter((c) => c.status !== "analyzed");

  return (
    <div className="flex flex-col gap-6">
      {/* Sayfa başlığı */}
      <div className="flex items-center gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20">
          <Shield className="h-5 w-5 text-indigo-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white">Uyum Raporları</h2>
          <p className="mt-0.5 text-sm text-slate-400">
            Analiz edilmiş sözleşmelerin uyum durumunu inceleyin
          </p>
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : contracts.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-5">
          {/* Uyum raporu hazır olanlar */}
          {analyzed.length > 0 && (
            <div className="flex flex-col gap-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Rapor Hazır ({analyzed.length})
              </h3>
              {analyzed.map((contract) => (
                <button
                  key={contract.id}
                  onClick={() =>
                    router.push(
                      `/dashboard/contracts/${contract.id}/compliance`
                    )
                  }
                  className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900 p-4 text-left transition hover:border-indigo-500/30 hover:bg-slate-800/60 active:scale-[0.99]"
                >
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-600/15">
                    <FileText className="h-5 w-5 text-indigo-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-slate-200">
                      {contract.title}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {new Date(contract.created_at).toLocaleDateString(
                        "tr-TR",
                        { day: "numeric", month: "long", year: "numeric" }
                      )}
                      {contract.original_filename && (
                        <> · {contract.original_filename}</>
                      )}
                    </p>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-400">
                      <Shield className="h-3 w-3" />
                      Raporu Gör
                    </span>
                    <ChevronRight className="h-4 w-4 text-slate-600" />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Rapor henüz hazır olmayanlar */}
          {others.length > 0 && (
            <div className="flex flex-col gap-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Analiz Bekleniyor ({others.length})
              </h3>
              {others.map((contract) => {
                const cfg =
                  STATUS_CONFIG[contract.status] ?? STATUS_CONFIG.uploaded;
                return (
                  <div
                    key={contract.id}
                    className="flex items-center gap-4 rounded-xl border border-slate-800/60 bg-slate-900/50 p-4 opacity-60"
                  >
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800">
                      <FileText className="h-5 w-5 text-slate-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-slate-400">
                        {contract.title}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-600">
                        {new Date(contract.created_at).toLocaleDateString(
                          "tr-TR",
                          { day: "numeric", month: "long", year: "numeric" }
                        )}
                      </p>
                    </div>
                    <div className="flex flex-shrink-0 items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${cfg.color}`}
                      >
                        {cfg.icon}
                        {cfg.label}
                      </span>
                      <Lock className="h-3.5 w-3.5 text-slate-700" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {analyzed.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/30 p-8 text-center">
              <Shield className="mx-auto h-10 w-10 text-slate-700" />
              <p className="mt-3 font-medium text-slate-400">
                Henüz uyum raporu oluşturulmadı
              </p>
              <p className="mt-1 text-sm text-slate-600">
                Bir sözleşmeyi analiz ettikten sonra uyum raporu burada görünür.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex h-64 items-center justify-center rounded-xl border border-slate-800 bg-slate-900">
      <div className="flex flex-col items-center gap-3 text-slate-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="text-sm">Yükleniyor…</span>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex h-64 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5">
      <div className="flex flex-col items-center gap-2 text-red-400">
        <AlertCircle className="h-8 w-8" />
        <span className="text-sm">{message}</span>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-slate-700 bg-slate-900/50">
      <Shield className="h-12 w-12 text-slate-700" />
      <div className="text-center">
        <p className="font-medium text-slate-400">Henüz sözleşme yüklenmedi</p>
        <p className="mt-1 text-sm text-slate-600">
          Sözleşme yükleyip analiz ettikten sonra raporlar burada görünür.
        </p>
      </div>
    </div>
  );
}
