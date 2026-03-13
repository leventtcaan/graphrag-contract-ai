"use client";

/**
 * Uyum Raporu Sayfası — Compliance Scoring
 * Premium dark-mode B2B SaaS stili: micro-interaction, gradient kart, hover efektleri.
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Shield,
  ArrowLeft,
  AlertTriangle,
  AlertCircle,
  Info,
  TrendingUp,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import api from "@/lib/api";

// ─── Tipler ────────────────────────────────────────────────────────────────────

interface ComplianceRisk {
  clause: string;
  risk_level: "High" | "Medium" | "Low";
  description: string;
}

interface ComplianceReport {
  score: number;
  summary: string;
  risks: ComplianceRisk[];
  recommendations: string[];
}

// ─── Sayfa ─────────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.get<ComplianceReport>(
          `/contracts/${id}/compliance`
        );
        setReport(data);
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response
            ?.data?.detail ??
          "Uyum raporu yüklenirken bir sorunla karşılaşıldı. Lütfen tekrar deneyin.";
        setError(detail);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [id]);

  return (
    <div className="flex flex-col gap-6">
      {/* Üst bar */}
      <div className="flex flex-wrap items-center gap-4">
        <button
          onClick={() => router.back()}
          className="group flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-slate-200"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Geri
        </button>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600/20 shadow-inner shadow-indigo-600/10">
            <Shield className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Uyum Raporu</h2>
            <p className="text-sm text-slate-400">
              Otomatik uyum skoru ve risk analizi
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : report ? (
        <ReportContent report={report} />
      ) : null}
    </div>
  );
}

// ─── Rapor İçeriği ─────────────────────────────────────────────────────────────

function ReportContent({ report }: { report: ComplianceReport }) {
  const isGood = report.score >= 75;
  const isMid = report.score >= 50 && report.score < 75;

  const scoreColor = isGood
    ? "text-emerald-400"
    : isMid
    ? "text-amber-400"
    : "text-red-400";

  const barColor = isGood
    ? "bg-gradient-to-r from-emerald-600 to-emerald-400"
    : isMid
    ? "bg-gradient-to-r from-amber-600 to-amber-400"
    : "bg-gradient-to-r from-red-700 to-red-500";

  const badgeCls = isGood
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
    : isMid
    ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
    : "border-red-500/30 bg-red-500/10 text-red-400";

  const scoreLabel = isGood ? "İyi Uyum" : isMid ? "Orta Uyum" : "Düşük Uyum";
  const ScoreIcon = isGood ? CheckCircle2 : isMid ? AlertCircle : AlertTriangle;

  const highCount = report.risks.filter((r) => r.risk_level === "High").length;
  const midCount = report.risks.filter(
    (r) => r.risk_level === "Medium"
  ).length;

  return (
    <div className="flex flex-col gap-5">
      {/* ── Skor Kartı ─────────────────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
        {/* Üst gradient şerit */}
        <div className={`h-1 w-full ${barColor}`} />

        <div className="p-6">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-2">
              <p className="text-sm text-slate-400">Genel Uyum Skoru</p>
              <div className="flex items-end gap-2">
                <span className={`text-6xl font-bold tabular-nums ${scoreColor}`}>
                  {report.score}
                </span>
                <span className="mb-2 text-2xl font-light text-slate-600">
                  /100
                </span>
              </div>
              <span
                className={`inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badgeCls}`}
              >
                <ScoreIcon className="h-3 w-3" />
                {scoreLabel}
              </span>
            </div>

            {/* Özet istatistikler */}
            <div className="flex flex-wrap gap-3">
              {highCount > 0 && (
                <StatPill
                  count={highCount}
                  label="Yüksek Risk"
                  color="text-red-400 bg-red-500/10 border-red-500/20"
                />
              )}
              {midCount > 0 && (
                <StatPill
                  count={midCount}
                  label="Orta Risk"
                  color="text-amber-400 bg-amber-500/10 border-amber-500/20"
                />
              )}
              {report.recommendations.length > 0 && (
                <StatPill
                  count={report.recommendations.length}
                  label="Öneri"
                  color="text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                />
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-5 h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out ${barColor}`}
              style={{ width: `${report.score}%` }}
            />
          </div>

          <p className="text-sm leading-relaxed text-slate-300">
            {report.summary}
          </p>
        </div>
      </div>

      {/* ── Riskler ────────────────────────────────────────────────────────── */}
      {report.risks.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Tespit Edilen Riskler{" "}
            <span className="text-slate-700">({report.risks.length})</span>
          </h3>
          <div className="flex flex-col gap-2.5">
            {report.risks.map((risk, i) => (
              <RiskCard key={i} risk={risk} />
            ))}
          </div>
        </div>
      )}

      {/* ── Öneriler ───────────────────────────────────────────────────────── */}
      {report.recommendations.length > 0 && (
        <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 to-transparent p-5 shadow-lg">
          <div className="mb-4 flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/15">
              <TrendingUp className="h-4 w-4 text-indigo-400" />
            </div>
            <h3 className="text-sm font-semibold text-indigo-300">
              Önerilen Aksiyonlar
            </h3>
          </div>
          <ul className="flex flex-col gap-3">
            {report.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-[3px] flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/15 text-[10px] font-bold text-indigo-400">
                  {i + 1}
                </span>
                <span className="leading-relaxed text-slate-300">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── İstatistik Etiketi ────────────────────────────────────────────────────────

function StatPill({
  count,
  label,
  color,
}: {
  count: number;
  label: string;
  color: string;
}) {
  return (
    <div
      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium ${color}`}
    >
      <span className="text-base font-bold tabular-nums">{count}</span>
      {label}
    </div>
  );
}

// ─── Risk Kartı ────────────────────────────────────────────────────────────────

const RISK_CONFIG = {
  High: {
    card: "border-red-500/20 bg-red-500/5 hover:border-red-500/40 hover:bg-red-500/10",
    badge: "bg-red-500/15 text-red-400 border border-red-500/25",
    clause: "text-red-300",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    label: "Yüksek Risk",
    dot: "bg-red-500",
  },
  Medium: {
    card: "border-amber-500/20 bg-amber-500/5 hover:border-amber-500/40 hover:bg-amber-500/10",
    badge: "bg-amber-500/15 text-amber-400 border border-amber-500/25",
    clause: "text-amber-300",
    icon: <AlertCircle className="h-3.5 w-3.5" />,
    label: "Orta Risk",
    dot: "bg-amber-500",
  },
  Low: {
    card: "border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/40 hover:bg-emerald-500/10",
    badge: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
    clause: "text-emerald-300",
    icon: <Info className="h-3.5 w-3.5" />,
    label: "Düşük Risk",
    dot: "bg-emerald-500",
  },
} as const;

function RiskCard({ risk }: { risk: ComplianceRisk }) {
  const cfg = RISK_CONFIG[risk.risk_level] ?? RISK_CONFIG["Medium"];

  return (
    <div
      className={`group rounded-xl border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg ${cfg.card}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${cfg.dot}`} />
            <span className={`text-sm font-semibold ${cfg.clause}`}>
              {risk.clause}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-slate-400">
            {risk.description}
          </p>
        </div>
        <span
          className={`inline-flex flex-shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${cfg.badge}`}
        >
          {cfg.icon}
          {cfg.label}
        </span>
      </div>
    </div>
  );
}

// ─── Yardımcı Durumlar ─────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="flex h-80 flex-col items-center justify-center gap-5 rounded-xl border border-slate-800 bg-slate-900">
      <div className="relative">
        <div className="h-16 w-16 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
        <Shield className="absolute inset-0 m-auto h-6 w-6 text-indigo-400" />
      </div>
      <div className="text-center">
        <p className="font-medium text-slate-300">Uyum raporu hazırlanıyor…</p>
        <p className="mt-1 text-sm text-slate-500">
          LLM analizi 15–30 saniye alabilir
        </p>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
      <AlertCircle className="h-8 w-8 text-red-400" />
      <p className="text-sm text-red-300">{message}</p>
    </div>
  );
}
