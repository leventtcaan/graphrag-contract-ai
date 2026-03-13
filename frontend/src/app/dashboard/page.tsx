"use client";

/**
 * Dashboard Ana Sayfası — Sözleşme Listesi
 * Arama, silme onayı, skeleton loader ve uyum raporu erişimi içeriyor.
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
  Shield,
  Trash2,
  Search,
  X,
} from "lucide-react";
import api from "@/lib/api";
import UploadModal from "@/components/ui/UploadModal";

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

const FALLBACK_STATUS = STATUS_CONFIG.uploaded;

// ─── Silme Onay Modalı ────────────────────────────────────────────────────────

function DeleteConfirmModal({
  contract,
  onConfirm,
  onCancel,
  deleting,
}: {
  contract: Contract;
  onConfirm: () => void;
  onCancel: () => void;
  deleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => !deleting && onCancel()}
      />
      {/* Modal */}
      <div className="relative z-10 mx-4 w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-5 flex items-start gap-3">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-red-500/15">
            <Trash2 className="h-4 w-4 text-red-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Sözleşmeyi Sil</h3>
            <p className="mt-1.5 text-sm text-slate-400">
              <span className="font-medium text-slate-200">
                &quot;{contract.title}&quot;
              </span>{" "}
              kalıcı olarak silinecek. Disk dosyası ve grafik verisi de
              kaldırılacak. Bu işlem geri alınamaz.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2.5">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-400 transition hover:bg-slate-800 disabled:opacity-50"
          >
            İptal
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-60"
          >
            {deleting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            {deleting ? "Siliniyor…" : "Kalıcı Olarak Sil"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Contract | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/contracts/${deleteTarget.id}`);
      setContracts((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      // Modal açık kalıyor — kullanıcı yeniden deneyebilir
    } finally {
      setDeleting(false);
    }
  };

  // Arama filtresi — büyük/küçük harf duyarsız
  const filtered = contracts.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

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

      {/* Arama barı — sadece en az 1 sözleşme varsa göster */}
      {!loading && !error && contracts.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Sözleşme adına göre ara…"
            className="w-full rounded-xl border border-slate-800 bg-slate-900 py-2.5 pl-10 pr-9 text-sm text-slate-200 placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
              aria-label="Aramayı temizle"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {/* İçerik alanı */}
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : contracts.length === 0 ? (
        <EmptyState onUpload={() => setModalOpen(true)} />
      ) : filtered.length === 0 ? (
        <NoResultsState search={search} onClear={() => setSearch("")} />
      ) : (
        <ContractTable
          contracts={filtered}
          onRowClick={(id) => router.push(`/dashboard/contracts/${id}`)}
          onDelete={(contract) => setDeleteTarget(contract)}
          onCompliance={(id) =>
            router.push(`/dashboard/contracts/${id}/compliance`)
          }
        />
      )}

      {/* Silme onay modalı */}
      {deleteTarget && (
        <DeleteConfirmModal
          contract={deleteTarget}
          onConfirm={handleDelete}
          onCancel={() => !deleting && setDeleteTarget(null)}
          deleting={deleting}
        />
      )}
    </div>
  );
}

// ─── Sözleşme Tablosu ─────────────────────────────────────────────────────────

function ContractTable({
  contracts,
  onRowClick,
  onDelete,
  onCompliance,
}: {
  contracts: Contract[];
  onRowClick: (id: string) => void;
  onDelete: (contract: Contract) => void;
  onCompliance: (id: string) => void;
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
            <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Uyum
            </th>
            <th className="w-10 px-2 py-3.5" />
            <th className="w-10 px-2 py-3.5" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {contracts.map((contract) =>
            contract.status === "processing" ? (
              <ProcessingRow
                key={contract.id}
                contract={contract}
                onDelete={onDelete}
              />
            ) : (
              <ContractRow
                key={contract.id}
                contract={contract}
                onRowClick={onRowClick}
                onDelete={onDelete}
                onCompliance={onCompliance}
              />
            )
          )}
        </tbody>
      </table>
    </div>
  );
}

// Satır: normal durum
function ContractRow({
  contract,
  onRowClick,
  onDelete,
  onCompliance,
}: {
  contract: Contract;
  onRowClick: (id: string) => void;
  onDelete: (contract: Contract) => void;
  onCompliance: (id: string) => void;
}) {
  const statusCfg = STATUS_CONFIG[contract.status] ?? FALLBACK_STATUS;

  return (
    <tr
      onClick={() => onRowClick(contract.id)}
      className="cursor-pointer transition hover:bg-slate-800/50 active:bg-slate-800"
    >
      <td className="px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800">
            <FileText className="h-4 w-4 text-slate-400" />
          </div>
          <span className="font-medium text-slate-200">{contract.title}</span>
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
      <td className="px-5 py-4">
        {contract.status === "analyzed" ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCompliance(contract.id);
            }}
            title="Uyum Raporunu Görüntüle"
            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-400 transition hover:bg-indigo-500/20 active:scale-95"
          >
            <Shield className="h-3.5 w-3.5" />
            Raporu Gör
          </button>
        ) : (
          <span className="text-slate-700">—</span>
        )}
      </td>
      <td className="px-2 py-4">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(contract);
          }}
          title="Sil"
          className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-600 transition hover:bg-red-500/10 hover:text-red-400"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </td>
      <td className="px-2 py-4 text-slate-600">
        <ChevronRight className="h-4 w-4" />
      </td>
    </tr>
  );
}

// Satır: işleniyor — skeleton animasyonu
function ProcessingRow({
  contract,
  onDelete,
}: {
  contract: Contract;
  onDelete: (contract: Contract) => void;
}) {
  return (
    <tr className="animate-pulse">
      <td className="px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800">
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-slate-300">
              {contract.title}
            </span>
            <div className="h-2 w-32 rounded-full bg-slate-700" />
          </div>
        </div>
      </td>
      <td className="px-5 py-4">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-400/20 bg-blue-400/10 px-2.5 py-1 text-xs font-medium text-blue-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          GraphRAG Analiz Ediliyor…
        </span>
      </td>
      <td className="px-5 py-4">
        <div className="h-3 w-28 rounded-full bg-slate-800" />
      </td>
      <td className="px-5 py-4">
        <div className="h-3 w-36 rounded-full bg-slate-800" />
      </td>
      <td className="px-5 py-4">
        <span className="text-slate-700">—</span>
      </td>
      <td className="px-2 py-4">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(contract);
          }}
          title="Sil"
          className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-600 transition hover:bg-red-500/10 hover:text-red-400"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </td>
      <td className="px-2 py-4 text-slate-800">
        <ChevronRight className="h-4 w-4" />
      </td>
    </tr>
  );
}

// ─── Yardımcı Durumlar ────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-5 py-3.5">
        <div className="h-3 w-24 rounded-full bg-slate-800" />
      </div>
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="flex animate-pulse items-center gap-4 border-b border-slate-800/60 px-5 py-4 last:border-0"
        >
          <div className="h-8 w-8 rounded-lg bg-slate-800" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="h-3 w-48 rounded-full bg-slate-800" />
            <div className="h-2 w-32 rounded-full bg-slate-800/60" />
          </div>
          <div className="h-5 w-20 rounded-full bg-slate-800" />
          <div className="h-3 w-24 rounded-full bg-slate-800" />
        </div>
      ))}
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
    <div className="flex h-72 flex-col items-center justify-center gap-5 rounded-xl border border-dashed border-slate-700 bg-slate-900/50">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800">
        <FileText className="h-8 w-8 text-slate-600" />
      </div>
      <div className="text-center">
        <p className="font-semibold text-slate-300">
          Henüz bir sözleşme yüklemediniz
        </p>
        <p className="mt-1.5 text-sm text-slate-500">
          IT sözleşmelerinizi yükleyip GraphRAG ile analiz etmeye başlayın.
          <br />
          Taraflar, maddeler ve yükümlülükler otomatik çıkarılır.
        </p>
      </div>
      <button
        onClick={onUpload}
        className="flex items-center gap-2 rounded-xl bg-indigo-600/20 px-5 py-2.5 text-sm font-semibold text-indigo-400 transition hover:bg-indigo-600/30"
      >
        <Plus className="h-4 w-4" />
        İlk Sözleşmeni Yükle
      </button>
    </div>
  );
}

function NoResultsState({
  search,
  onClear,
}: {
  search: string;
  onClear: () => void;
}) {
  return (
    <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-xl border border-slate-800 bg-slate-900/50">
      <Search className="h-8 w-8 text-slate-700" />
      <div className="text-center">
        <p className="font-medium text-slate-400">Sonuç bulunamadı</p>
        <p className="mt-1 text-sm text-slate-600">
          &quot;{search}&quot; ile eşleşen sözleşme yok.
        </p>
      </div>
      <button
        onClick={onClear}
        className="flex items-center gap-1.5 text-sm text-indigo-400 transition hover:text-indigo-300"
      >
        <X className="h-3.5 w-3.5" />
        Aramayı Temizle
      </button>
    </div>
  );
}
