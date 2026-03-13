/**
 * Paylaşılan Sözleşme Tipleri
 * Backend ContractStatus enum değerleriyle birebir eşleşiyor (küçük harf).
 * Bu dosyayı hem dashboard hem detay sayfası import ediyor.
 */

export type ContractStatus =
  | "uploaded"
  | "processing"
  | "analyzed"
  | "failed"
  | "archived";

export interface Contract {
  id: string;
  title: string;
  description: string | null;
  status: ContractStatus;
  created_at: string;
  updated_at: string;
  original_filename: string | null;
  file_path: string | null;
  neo4j_node_id: string | null;
}

export interface ChatMessage {
  role: "user" | "ai";
  content: string;
  /** GraphRAG'ın ürettiği Cypher sorgusu (opsiyonel, debug için) */
  cypher?: string | null;
}
