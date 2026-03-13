"use client";

/**
 * GraphRAG Chat Bileşeni
 * Kullanıcının sözleşmeye doğal dilde soru sormasını sağlar.
 * POST /contracts/{id}/chat — { question } → { answer, generated_cypher }
 */

import { useEffect, useRef, useState } from "react";
import { Send, Bot, User, Loader2, ChevronDown, ChevronUp, Code2 } from "lucide-react";
import api from "@/lib/api";
import { ChatMessage } from "@/types/contract";

interface ContractChatProps {
  contractId: string;
  /** Sözleşme analiz edilmediyse chat devre dışı bırakılır */
  isAnalyzed: boolean;
}

interface ChatApiResponse {
  answer: string;
  context_nodes: unknown[];
  generated_cypher: string | null;
}

export default function ContractChat({
  contractId,
  isAnalyzed,
}: ContractChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Yeni mesaj gelince sohbet alanını en alta kaydır
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || thinking) return;

    // Kullanıcı mesajını anında ekle
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setThinking(true);

    try {
      const { data } = await api.post<ChatApiResponse>(
        `/contracts/${contractId}/chat`,
        { question }
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: data.answer,
          cypher: data.generated_cypher,
        },
      ]);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Bir hata oluştu. Lütfen tekrar deneyin.";
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: `Hata: ${detail}` },
      ]);
    } finally {
      setThinking(false);
      // Cevap geldikten sonra input'a odaklan
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      {/* Chat başlığı */}
      <div className="flex items-center gap-2.5 border-b border-slate-800 px-4 py-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600/20">
          <Bot className="h-4 w-4 text-indigo-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-white">GraphRAG Asistan</p>
          <p className="text-xs text-slate-500">
            {isAnalyzed
              ? "Sözleşme hakkında soru sorun"
              : "Sözleşme analiz bekleniyor"}
          </p>
        </div>
      </div>

      {/* Mesaj listesi */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        {messages.length === 0 && !thinking && (
          <WelcomeHints isAnalyzed={isAnalyzed} />
        )}

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <UserBubble key={i} content={msg.content} />
          ) : (
            <AiBubble key={i} content={msg.content} cypher={msg.cypher} />
          )
        )}

        {/* "Yapay Zeka Düşünüyor" animasyonu */}
        {thinking && <ThinkingIndicator />}

        {/* Otomatik kaydırma için boş referans noktası */}
        <div ref={bottomRef} />
      </div>

      {/* Input alanı */}
      <div className="border-t border-slate-800 p-3">
        <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isAnalyzed || thinking}
            placeholder={
              isAnalyzed
                ? "Sorunuzu yazın… (Enter ile gönderin)"
                : "Sözleşme analizi tamamlandıktan sonra soru sorabilirsiniz"
            }
            className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSend}
            disabled={!isAnalyzed || thinking || !input.trim()}
            className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Gönder"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Alt bileşenler ────────────────────────────────────────────────────────

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end gap-2.5">
      <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-sm text-white">
        {content}
      </div>
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-slate-700">
        <User className="h-3.5 w-3.5 text-slate-300" />
      </div>
    </div>
  );
}

function AiBubble({
  content,
  cypher,
}: {
  content: string;
  cypher?: string | null;
}) {
  const [showCypher, setShowCypher] = useState(false);

  return (
    <div className="flex gap-2.5">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600/20">
        <Bot className="h-3.5 w-3.5 text-indigo-400" />
      </div>
      <div className="flex max-w-[80%] flex-col gap-2">
        <div className="rounded-2xl rounded-tl-sm bg-slate-800 px-4 py-2.5 text-sm leading-relaxed text-slate-200">
          {content}
        </div>

        {/* Cypher debug paneli — varsa göster */}
        {cypher && (
          <div className="overflow-hidden rounded-lg border border-slate-700">
            <button
              onClick={() => setShowCypher((v) => !v)}
              className="flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-xs text-slate-500 transition hover:bg-slate-800/50"
            >
              <Code2 className="h-3 w-3" />
              Cypher Sorgusu
              {showCypher ? (
                <ChevronUp className="ml-auto h-3 w-3" />
              ) : (
                <ChevronDown className="ml-auto h-3 w-3" />
              )}
            </button>
            {showCypher && (
              <pre className="overflow-x-auto bg-slate-950 px-3 py-2 text-xs text-emerald-400">
                {cypher}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex gap-2.5">
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600/20">
        <Bot className="h-3.5 w-3.5 text-indigo-400" />
      </div>
      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-slate-800 px-4 py-3">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
        <span className="text-sm text-slate-400">Yapay zeka düşünüyor…</span>
      </div>
    </div>
  );
}

function WelcomeHints({ isAnalyzed }: { isAnalyzed: boolean }) {
  if (!isAnalyzed) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-600" />
        <p className="text-sm text-slate-500">
          Sözleşme analiz edildiğinde soru sorabileceksiniz.
        </p>
      </div>
    );
  }

  const hints = [
    "Bu sözleşmedeki taraflar kimlerdir?",
    "Gizlilik maddeleri nelerdir?",
    "Sözleşme hangi yükümlülükleri içeriyor?",
    "Fesih koşulları nelerdir?",
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-6">
      <Bot className="h-10 w-10 text-slate-700" />
      <p className="text-sm text-slate-500">
        Sözleşme hakkında bir şey sorun. Örneğin:
      </p>
      <div className="flex flex-col gap-2 w-full max-w-xs">
        {hints.map((hint) => (
          <div
            key={hint}
            className="rounded-lg border border-slate-800 bg-slate-800/50 px-3 py-2 text-xs text-slate-400"
          >
            "{hint}"
          </div>
        ))}
      </div>
    </div>
  );
}
