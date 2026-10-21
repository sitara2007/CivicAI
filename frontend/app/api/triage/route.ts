import https from "node:https";
import { API_BASE } from "@/lib/api";

export const runtime = "nodejs";

const maxTextLength = 100_000;
const maxRequestBytes = 1_048_576;

interface RedactionResponse {
  redacted_text: string;
  pii_entities_masked: number;
}

function redactWithGo(text: string): Promise<RedactionResponse> {
  const endpoint = process.env.GO_INGEST_URL;
  const cert = process.env.GO_INGEST_CLIENT_CERT;
  const key = process.env.GO_INGEST_CLIENT_KEY;
  const ca = process.env.GO_INGEST_SERVER_CA;
  if (!endpoint || !cert || !key || !ca) {
    throw new Error("Go ingest mTLS is not configured on the server.");
  }

  const target = new URL(endpoint);
  if (target.protocol !== "https:") {
    throw new Error("Go ingest endpoint must use HTTPS.");
  }

  return new Promise((resolve, reject) => {
    const request = https.request(
      target,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cert,
        key,
        ca,
      },
      (response) => {
        const chunks: Buffer[] = [];
        let size = 0;
        response.on("data", (chunk: Buffer) => {
          size += chunk.length;
          if (size > 1_048_576) {
            request.destroy(new Error("Go ingest response exceeded the size limit."));
            return;
          }
          chunks.push(chunk);
        });
        response.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          if (!response.statusCode || response.statusCode < 200 || response.statusCode >= 300) {
            reject(new Error(`Go ingest returned HTTP ${response.statusCode ?? "unknown"}.`));
            return;
          }
          try {
            const result: unknown = JSON.parse(body);
            if (
              typeof result !== "object" ||
              result === null ||
              !("redacted_text" in result) ||
              typeof result.redacted_text !== "string" ||
              !("pii_entities_masked" in result) ||
              typeof result.pii_entities_masked !== "number" ||
              !Number.isSafeInteger(result.pii_entities_masked) ||
              result.pii_entities_masked < 0
            ) {
              reject(new Error("Go ingest returned an invalid redaction response."));
              return;
            }
            resolve({
              redacted_text: result.redacted_text,
              pii_entities_masked: result.pii_entities_masked,
            });
          } catch (error) {
            reject(error);
          }
        });
      },
    );
    request.setTimeout(5_000, () => request.destroy(new Error("Go ingest request timed out.")));
    request.on("error", reject);
    request.end(JSON.stringify({ text }));
  });
}

async function readJSONLimited(request: Request): Promise<unknown> {
  if (!request.body) {
    throw new SyntaxError("Request body is empty.");
  }
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > maxRequestBytes) {
      await reader.cancel();
      throw new RangeError("Request body is too large.");
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function POST(request: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await readJSONLimited(request);
  } catch (error) {
    if (error instanceof RangeError) {
      return Response.json({ detail: "Request body exceeds the size limit." }, { status: 413 });
    }
    return Response.json({ detail: "Request body must be valid JSON." }, { status: 400 });
  }
  if (
    typeof body !== "object" ||
    body === null ||
    !("text" in body) ||
    typeof body.text !== "string" ||
    !body.text.trim() ||
    body.text.length > maxTextLength
  ) {
    return Response.json({ detail: "Provide one non-empty text document of at most 100,000 characters." }, { status: 422 });
  }
  const sourceType = "source_type" in body ? body.source_type : "text";
  if (sourceType !== "text" && sourceType !== "pdf" && sourceType !== "form") {
    return Response.json({ detail: "The document source type is invalid." }, { status: 422 });
  }

  try {
    const redaction = await redactWithGo(body.text);
    const response = await fetch(`${API_BASE}/api/v1/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: redaction.redacted_text, source_type: sourceType }),
      signal: AbortSignal.timeout(30_000),
    });
    const result: unknown = await response.json();
    if (!response.ok) {
      return Response.json({ detail: `Classification service returned HTTP ${response.status}.` }, { status: 502 });
    }
    if (typeof result !== "object" || result === null) {
      return Response.json({ detail: "Classification service returned an invalid response." }, { status: 502 });
    }
    return Response.json(
      {
        ...result,
        pii_entities_masked: redaction.pii_entities_masked,
      },
      { status: response.status },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Document triage failed.";
    return Response.json({ detail: message }, { status: 502 });
  }
}
