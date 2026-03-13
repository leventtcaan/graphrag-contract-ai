"use client";

/**
 * Sözleşme Yükleme Modalı
 *
 * Üç aşamalı asenkron pipeline'ı tek UX akışında birleştirir:
 *   1. POST /contracts/       — metadata kaydı (id alınır)
 *   2. POST /contracts/{id}/upload  — PDF dosyası yüklenir
 *   3. POST /contracts/{id}/analyze — GraphRAG analizi tetiklenir
 *
 * Her aşama için ayrı loading mesajı gösterilir; hata herhangi bir
 * aşamada oluşursa kullanıcıya bildirilir ve modal açık kalır.
 */

import { useRef, useState } from "react";
import { Loader2, UploadCloud, FileText, CheckCircle2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Tipler ────────────────────────────────────────────────────────────────

interface ContractResponse {
  id: string;
  title: string;
  status: string;
}

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Yükleme + analiz başarıyla tamamlanınca çağrılır (tabloyu yenilemek için) */
  onSuccess: () => void;
}

// Kullanıcıya gösterilecek aşama mesajları
type Stage = "idle" | "creating" | "uploading" | "analyzing" | "done";

const STAGE_MESSAGES: Record<Stage, string> = {
  idle: "",
  creating: "Sözleşme kaydı oluşturuluyor…",
  uploading: "PDF yükleniyor…",
  analyzing: "GraphRAG analizi başlatılıyor…",
  done: "Tamamlandı!",
};

// ─── Bileşen ───────────────────────────────────────────────────────────────

export default function UploadModal({
  open,
  onOpenChange,
  onSuccess,
}: UploadModalProps) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isBusy = stage !== "idle" && stage !== "done";

  const resetForm = () => {
    setTitle("");
    setFile(null);
    setStage("idle");
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleOpenChange = (next: boolean) => {
    // İşlem devam ediyorken modalı kapatmaya izin verme
    if (isBusy) return;
    if (!next) resetForm();
    onOpenChange(next);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setError(null);

    try {
      // ── Aşama 1: Sözleşme metadata kaydı ──────────────────────────────
      setStage("creating");
      const { data: contract } = await api.post<ContractResponse>(
        "/contracts/",
        { title: title.trim() }
      );
      const contractId = contract.id;

      // ── Aşama 2: PDF dosyasını yükle ───────────────────────────────────
      setStage("uploading");
      const formData = new FormData();
      // Backend "file" field adını bekliyor (UploadFile parametresi)
      formData.append("file", file);
      await api.post(`/contracts/${contractId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // ── Aşama 3: GraphRAG analizini tetikle ────────────────────────────
      setStage("analyzing");
      await api.post(`/contracts/${contractId}/analyze`);

      // ── Başarı ─────────────────────────────────────────────────────────
      setStage("done");
      // Kısa bir "Tamamlandı" gösterimi ardından modalı kapat ve tabloyu yenile
      setTimeout(() => {
        resetForm();
        onOpenChange(false);
        onSuccess();
      }, 1200);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Bir hata oluştu. Lütfen tekrar deneyin.";
      setError(detail);
      // Hata durumunda kullanıcı tekrar deneyebilmeli
      setStage("idle");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="border-slate-800 bg-slate-900 text-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <UploadCloud className="h-5 w-5 text-indigo-400" />
            Yeni Sözleşme Yükle
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            PDF dosyanızı seçin ve analiz için gönderin.
          </DialogDescription>
        </DialogHeader>

        {/* İşlem tamamlandı durumu */}
        {stage === "done" ? (
          <div className="flex flex-col items-center gap-3 py-8">
            <CheckCircle2 className="h-12 w-12 text-emerald-400" />
            <p className="font-medium text-emerald-400">Analiz başlatıldı!</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-2">
            {/* Sözleşme Adı */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="contract-title"
                className="text-sm font-medium text-slate-300"
              >
                Sözleşme Adı
              </label>
              <input
                id="contract-title"
                type="text"
                required
                disabled={isBusy}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Örn: ACME Corp. - Yazılım Lisans Sözleşmesi"
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            {/* PDF Dosya Seçimi */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="contract-file"
                className="text-sm font-medium text-slate-300"
              >
                PDF Dosyası
              </label>

              {/* Özel dosya seçim alanı */}
              <div
                onClick={() => !isBusy && fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 transition ${
                  file
                    ? "border-indigo-500/50 bg-indigo-500/5"
                    : "border-slate-700 hover:border-slate-600"
                } ${isBusy ? "cursor-not-allowed opacity-50" : ""}`}
              >
                {file ? (
                  <>
                    <FileText className="h-8 w-8 text-indigo-400" />
                    <span className="text-sm font-medium text-slate-300">
                      {file.name}
                    </span>
                    <span className="text-xs text-slate-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="h-8 w-8 text-slate-500" />
                    <span className="text-sm text-slate-400">
                      Tıklayarak PDF seçin
                    </span>
                    <span className="text-xs text-slate-600">
                      Yalnızca .pdf dosyaları
                    </span>
                  </>
                )}
              </div>

              <input
                ref={fileInputRef}
                id="contract-file"
                type="file"
                accept=".pdf"
                className="hidden"
                disabled={isBusy}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>

            {/* Hata mesajı */}
            {error && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                {error}
              </p>
            )}

            {/* İlerleme durumu */}
            {isBusy && (
              <div className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-2.5">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
                <span className="text-sm text-slate-300">
                  {STAGE_MESSAGES[stage]}
                </span>
              </div>
            )}

            {/* Aksiyon butonları */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={isBusy}
                onClick={() => handleOpenChange(false)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                İptal
              </button>
              <button
                type="submit"
                disabled={isBusy || !file || !title.trim()}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UploadCloud className="h-4 w-4" />
                )}
                {isBusy ? "İşleniyor…" : "Yükle ve Analiz Et"}
              </button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
