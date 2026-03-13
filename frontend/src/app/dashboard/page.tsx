"use client";

/**
 * Dashboard Ana Sayfası — Sözleşme Listesi
 * Sayfa yüklendiğinde ve her başarılı yüklemede /contracts endpoint'inden veri çeker.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Archive,
  ChevronRight,
} from "lucide-react";
import api from "@/lib/api";
import UploadModal from "@/components/ui/UploadModal";

// Backend ContractStatus enum değerleri (küçük harf string)
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

// Backend status string'inden görsel konfigürasyona eşleme
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

// Bilinmeyen status değerleri için yedek
const FALLBACK_STATUS = STATUS_CONFIG.uploaded;

export default function DashboardPage() {
  const router = useRouter();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // useCallback: onSuccess prop'u her render'da yeni referans oluşturmasın
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

  return (
    <div className="flex flex-col gap-6">
      {/* Sayfa başlığı + aksiyon butonu */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Sözleşmeler</h2>
          <p className="mt-0.5 text-sm text-slate-400">
            Yüklenen ve analiz edilen tüm sözleşmeleriniz
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500 active:scale-95"
        >
          <Plus className="h-4 w-4" />
          Yeni Sözleşme Yükle
        </button>
      </div>

      {/* Yükleme modalı */}
      <UploadModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSuccess={fetchContracts}
      />

      {/* İçerik alanı */}
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : contracts.length === 0 ? (
        <EmptyState onUpload={() => setModalOpen(true)} />
      ) : (
        <ContractTable
          contracts={contracts}
          onRowClick={(id) => router.push(`/dashboard/contracts/${id}`)}
        />
      )}
    </div>
  );
}

// ─── Alt bileşenler ────────────────────────────────────────────────────────

function ContractTable({
  contracts,
  onRowClick,
}: {
  contracts: Contract[];
  onRowClick: (id: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Sözleşme Adı
            </th>
            <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Durum
            </th>
            <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Yüklenme Tarihi
            </th>
            <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Dosya
            </th>
            <th className="w-10 px-2 py-3.5" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {contracts.map((contract) => {
            const statusCfg =
              STATUS_CONFIG[contract.status] ?? FALLBACK_STATUS;
            return (
              <tr
                key={contract.id}
                onClick={() => onRowClick(contract.id)}
                className="cursor-pointer transition hover:bg-slate-800/50 active:bg-slate-800"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800">
                      <FileText className="h-4 w-4 text-slate-400" />
                    </div>
                    <span className="font-medium text-slate-200">
                      {contract.title}
                    </span>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${statusCfg.color}`}
                  >
                    {statusCfg.icon}
                    {statusCfg.label}
                  </span>
                </td>
                <td className="px-5 py-4 text-slate-400">
                  {new Date(contract.created_at).toLocaleDateString("tr-TR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </td>
                <td className="px-5 py-4 text-slate-500">
                  {contract.original_filename ?? "—"}
                </td>
                <td className="px-2 py-4 text-slate-600">
                  <ChevronRight className="h-4 w-4" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex h-64 items-center justify-center rounded-xl border border-slate-800 bg-slate-900">
      <div className="flex flex-col items-center gap-3 text-slate-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="text-sm">Sözleşmeler yükleniyor…</span>
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

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-slate-700 bg-slate-900/50">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-800">
        <FileText className="h-7 w-7 text-slate-500" />
      </div>
      <div className="text-center">
        <p className="font-medium text-slate-300">Henüz sözleşme yok</p>
        <p className="mt-1 text-sm text-slate-500">
          İlk sözleşmenizi yükleyerek analize başlayın
        </p>
      </div>
      <button
        onClick={onUpload}
        className="flex items-center gap-2 rounded-lg bg-indigo-600/20 px-4 py-2 text-sm font-medium text-indigo-400 transition hover:bg-indigo-600/30"
      >
        <Plus className="h-4 w-4" />
        Sözleşme Yükle
      </button>
    </div>
  );
}
