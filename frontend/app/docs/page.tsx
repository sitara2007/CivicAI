export default function DocsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20 text-[#EDEDED]">
      <h1 className="text-4xl font-semibold tracking-tight">API Documentation</h1>
      <p className="mt-4 text-[#8A8A8A]">POST /api/v1/process</p>
      <h2 className="mt-12 text-2xl font-semibold">Request</h2>
      <pre className="mt-4 overflow-auto rounded-md border border-[#1F1F1F] bg-[#111111] p-4 font-mono text-xs">{`curl -X POST https://civicai-backend-hb5e.onrender.com/api/v1/process \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Your document text"}'`}</pre>
      <h2 className="mt-12 text-2xl font-semibold">Response</h2>
      <pre className="mt-4 overflow-auto rounded-md border border-[#1F1F1F] bg-[#111111] p-4 font-mono text-xs">{`{
  "classification": "rti_request",
  "pii_redacted": true,
  "audit_hash": "sha256:...",
  "latency_ms": 47
}`}</pre>
    </main>
  );
}
