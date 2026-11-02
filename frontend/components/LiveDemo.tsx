"use client";
import { useState } from "react";
import { Loader } from "lucide-react";
export function LiveDemo() {
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit() {
    if (!text.trim()) return;
    setLoading(true); setError(""); setResult("");
    try {
      const res = await fetch("https://civicai-backend-hb5e.onrender.com/api/v1/process", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) setError(JSON.stringify(data, null, 2));
      else setResult(JSON.stringify(data, null, 2));
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="mb-8 text-2xl font-semibold text-[#EDEDED]">Try it live</h2>
      <div className="rounded-lg border border-[#1F1F1F] bg-[#111111] p-6">
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste a government document..."
          className="h-40 w-full rounded-md border border-[#1F1F1F] bg-[#0A0A0A] p-4 font-mono text-sm text-[#EDEDED] outline-none focus:border-[#00D4AA]" />
        <button onClick={submit} disabled={loading || !text.trim()}
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#00D4AA] px-5 py-3 text-sm font-medium text-black hover:bg-[#2BE6BC] disabled:opacity-50">
          {loading && <Loader size={16} className="animate-spin" />}
          {loading ? "Processing..." : "Process Document"}
        </button>
        {error && <pre className="mt-6 overflow-auto rounded-md border border-red-900 bg-[#0A0A0A] p-4 font-mono text-xs text-red-400">{error}</pre>}
        {result && <pre className="mt-6 overflow-auto rounded-md border border-[#1F1F1F] bg-[#0A0A0A] p-4 font-mono text-xs text-[#EDEDED]">{result}</pre>}
      </div>
    </section>
  );
}
