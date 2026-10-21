export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "https://civicos-480a.onrender.com";

export type SourceType = "text" | "pdf" | "form";

export interface ProcessDecision {
  category: "Complaint" | "Request" | "Report" | "Other";
  priority: "Low" | "Medium" | "High" | "Critical";
  department: string;
  confidence: number;
  decision_rationale: string;
  summary: string;
}

export interface ProcessResponse {
  trace_id: string;
  document_id: string;
  status: string;
  decision: ProcessDecision | null;
  requires_review: boolean;
  hop_count: number | null;
  pii_entities_masked: number;
  redacted_text: string | null;
  audit_hash: string | null;
  created_at: string;
}

export async function processDocument(text: string, sourceType: SourceType): Promise<ProcessResponse> {
  const res = await fetch(`${API_BASE}/api/v1/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_type: sourceType }),
    signal: AbortSignal.timeout(30_000),
  });

  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const payload = data as { detail?: unknown; message?: unknown } | null;
    const detail = payload?.detail;
    const message = typeof detail === "string"
      ? detail
      : typeof detail === "object" && detail !== null && "message" in detail && typeof detail.message === "string"
        ? detail.message
        : typeof payload?.message === "string"
          ? payload.message
          : `The processing service returned ${res.status}.`;
    throw new Error(message);
  }

  return data as ProcessResponse;
}

export async function triageDocument(text: string, sourceType: SourceType): Promise<ProcessResponse> {
  const res = await fetch("/api/triage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_type: sourceType }),
    signal: AbortSignal.timeout(35_000),
  });

  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const payload = data as { detail?: unknown; message?: unknown } | null;
    const detail = payload?.detail;
    const message = typeof detail === "string"
      ? detail
      : typeof payload?.message === "string"
        ? payload.message
        : `The processing service returned ${res.status}.`;
    throw new Error(message);
  }

  return data as ProcessResponse;
}
