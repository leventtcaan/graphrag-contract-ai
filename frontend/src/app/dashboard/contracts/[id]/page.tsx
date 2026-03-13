"use client";

/**
 * Sözleşme Detay Sayfası — Split-Screen Layout
 * Sol: sözleşme metadata kartı  |  Sağ: GraphRAG chat arayüzü
 *
 * Next.js 15+ App Router'da params bir Promise — React.use() ile açıyoruz.
 */

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Archive,
  Calendar,
  HardDrive,
  Sparkles,
} from "lucide-react";
import api from "@/lib/api";
import { Contract, ContractStatus } from "@/types/contract";
import ContractChat from "@/components/ui/ContractChat";

// Status görsel konfigürasyonu (dashboard ile aynı palet)
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

// ─── Sayfa Bileşeni ────────────────────────────────────────────────────────

export default function ContractDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // Next.js 15+ — params Promise'ini React.use() ile çözüyoruz
  const { id } = use(params);
  const router = useRouter();

  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContract = async () => {
      try {
        const { data } = await api.get<Contract>(`/contracts/${id}`);
        setContract(data);
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response
          ?.status;
        setError(
          status === 404
            ? "Sözleşme bulunamadı."
            : "Sözleşme yüklenirken hata oluştu."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchContract();
  }, [id]);

  // ── Yükleniyor ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="text-sm">Yükleniyor…</span>
        </div>
      </div>
    );
  }

  // ── Hata ───────────────────────────────────────────────────────────────
  if (error || !contract) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <AlertCircle className="h-10 w-10 text-red-400" />
        <p className="text-slate-400">{error ?? "Bilinmeyen hata."}</p>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Geri Dön
        </button>
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[contract.status] ?? STATUS_CONFIG.uploaded;
  const isAnalyzed = contract.status === "analyzed";

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Üst navigasyon şeridi */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-slate-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Sözleşmeler
        </button>
        <span className="text-slate-700">/</span>
        <span className="text-sm text-slate-300 font-medium truncate max-w-xs">
          {contract.title}
        </span>
      </div>

      {/* Split-Screen: Sol kart + Sağ chat */}
      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[380px_1fr]">
        {/* ── Sol: Sözleşme Bilgi Kartı ─────────────────────────────── */}
        <div className="flex flex-col gap-4 overflow-y-auto">
          {/* Metadata kartı */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            {/* İkon + başlık */}
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-600/15">
                <FileText className="h-5 w-5 text-indigo-400" />
              </div>
              <div className="min-w-0">
                <h2 className="break-words font-semibold leading-snug text-white">
                  {contract.title}
                </h2>
                {contract.description && (
                  <p className="mt-1 text-xs text-slate-500">
                    {contract.description}
                  </p>
                )}
              </div>
            </div>

            {/* Durum badge */}
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${statusCfg.color}`}
            >
              {statusCfg.icon}
              {statusCfg.label}
            </span>

            {/* Meta bilgiler */}
            <div className="mt-4 flex flex-col gap-2.5 border-t border-slate-800 pt-4">
              <MetaRow
                icon={<Calendar className="h-3.5 w-3.5" />}
                label="Yüklenme"
                value={new Date(contract.created_at).toLocaleDateString(
                  "tr-TR",
                  { day: "numeric", month: "long", year: "numeric" }
                )}
              />
              {contract.original_filename && (
                <MetaRow
                  icon={<HardDrive className="h-3.5 w-3.5" />}
                  label="Dosya"
                  value={contract.original_filename}
                />
              )}
              {contract.neo4j_node_id && (
                <MetaRow
                  icon={<Sparkles className="h-3.5 w-3.5" />}
                  label="Graf Düğümü"
                  value={contract.neo4j_node_id}
                  mono
                />
              )}
            </div>
          </div>

          {/* GraphRAG bilgi kartı */}
          {isAnalyzed && (
            <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
              <div className="flex items-start gap-2.5">
                <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-indigo-400" />
                <div>
                  <p className="text-sm font-medium text-indigo-300">
                    GraphRAG Analizi Tamamlandı
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-indigo-400/70">
                    Bu belge GraphRAG motoru tarafından analiz edildi. Sözleşmedeki
                    taraflar, maddeler, yükümlülükler ve yasal referanslar bilgi
                    grafiğine aktarıldı. Sağ taraftan sorularınızı sorabilirsiniz.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Analiz bekleniyor uyarısı */}
          {!isAnalyzed && contract.status !== "failed" && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <div className="flex items-start gap-2.5">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
                <div>
                  <p className="text-sm font-medium text-amber-300">
                    Analiz Bekleniyor
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-amber-400/70">
                    Sözleşme henüz GraphRAG motoru tarafından işlenmedi.
                    Chat özelliği analiz tamamlandıktan sonra aktif olacak.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Sağ: Chat Arayüzü ─────────────────────────────────────── */}
        <ContractChat contractId={id} isAnalyzed={isAnalyzed} />
      </div>
    </div>
  );
}

// ─── Yardımcı bileşenler ───────────────────────────────────────────────────

function MetaRow({
  icon,
  label,
  value,
  mono = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="mt-0.5 flex-shrink-0 text-slate-500">{icon}</span>
      <span className="w-16 flex-shrink-0 text-slate-500">{label}</span>
      <span
        className={`break-all text-slate-300 ${mono ? "font-mono text-[10px]" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}
