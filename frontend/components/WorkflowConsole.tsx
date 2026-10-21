"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Check,
  Clipboard,
  FileInput,
  FileText,
  LoaderCircle,
  LockKeyhole,
  Route,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { Nav } from "@/components/Nav";
import { triageDocument, type ProcessResponse, type SourceType } from "@/lib/api";

const examples = [
  {
    label: "Urgent water issue",
    sourceType: "text" as const,
    text: "A water main has burst on Cedar Avenue and several nearby basements are flooding. Please send a crew as soon as possible.",
  },
  {
    label: "Property records request",
    sourceType: "form" as const,
    text: "Please provide a copy of the latest property tax assessment for 18 Oak Street.",
  },
];

const sourceOptions: { value: SourceType; label: string }[] = [
  { value: "text", label: "Pasted text" },
  { value: "pdf", label: "PDF text" },
  { value: "form", label: "Form response" },
];

function priorityClass(priority: string) {
  if (priority === "Critical" || priority === "High") {
    return "border-red-400/30 bg-red-400/10 text-red-300";
  }
  if (priority === "Medium") {
    return "border-amber-300/30 bg-amber-300/10 text-amber-200";
  }
  return "border-emerald-300/30 bg-emerald-300/10 text-emerald-200";
}

export function WorkflowConsole() {
  const [text, setText] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("text");
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [fileName, setFileName] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim() || loading) return;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await triageDocument(text, sourceType));
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "The document could not be processed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function loadTextFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt") && file.type !== "text/plain") {
      setError("Choose a plain-text (.txt) document.");
      return;
    }
    if (file.size > 400_000) {
      setError("The text document exceeds the 100,000-character limit.");
      return;
    }
    try {
      const content = await file.text();
      if (!content.trim() || content.length > 100_000) {
        setError("Choose a non-empty text document of at most 100,000 characters.");
        return;
      }
      setText(content);
      setSourceType("text");
      setFileName(file.name);
      setError("");
      setResult(null);
    } catch {
      setError("The text document could not be read.");
    }
  }

  async function copyTraceId() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.trace_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Clipboard access is unavailable in this browser.");
    }
  }

  function loadExample(example: (typeof examples)[number]) {
    setText(example.text);
    setSourceType(example.sourceType);
    setError("");
    setResult(null);
  }

  const decision = result?.decision;

  return (
    <main className="min-h-screen bg-[#101311] text-[#f1f2ed]">
      <Nav />
      <div className="mx-auto max-w-7xl px-5 pb-16 pt-9 sm:px-8">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-5">
          <div className="flex items-center gap-2 text-xs text-[#a5aaa2]">
            <Link href="/" className="hover:text-white">CivicOs</Link>
            <span aria-hidden="true">/</span>
            <span className="text-[#f1f2ed]">Intake workflow</span>
          </div>
          <span className="inline-flex items-center gap-2 text-xs text-[#a5aaa2]">
            <span className="h-2 w-2 rounded-full bg-[#92d6a4]" />
            Public correspondence
          </span>
        </div>

        <header className="mb-8 max-w-3xl">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#92d6a4]">
            Citizen services / document triage
          </p>
          <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">Triage a new submission</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[#a5aaa2]">
            Redact personal information, classify the request, and surface the department best suited to respond.
          </p>
        </header>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
          <section className="border border-white/10 bg-[#171b18]">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center border border-white/10 bg-[#202621] text-[#a7d9b0]">
                  <FileInput size={16} />
                </span>
                <div>
                  <h2 className="text-sm font-semibold">Submission details</h2>
                  <p className="mt-0.5 text-xs text-[#929990]">Paste extracted text to begin triage</p>
                </div>
              </div>
              <span className="font-mono text-xs text-[#929990]">01 / 02</span>
            </div>

            <form onSubmit={submit} className="p-5">
              <fieldset>
                <legend className="mb-2 text-xs font-medium text-[#c7ccc4]">Intake source</legend>
                <div className="grid grid-cols-3 border border-white/10" role="group" aria-label="Intake source">
                  {sourceOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={sourceType === option.value}
                      onClick={() => setSourceType(option.value)}
                      className={`min-h-10 border-r border-white/10 px-2 text-xs last:border-r-0 ${sourceType === option.value ? "bg-[#28352b] text-[#c5edcc]" : "text-[#a5aaa2] hover:bg-white/5 hover:text-white"}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </fieldset>

              <div className="mt-5 flex items-center justify-between gap-3">
                <label htmlFor="submission-text" className="text-xs font-medium text-[#c7ccc4]">Document text</label>
                <span className="font-mono text-[11px] text-[#838a81]">{text.length.toLocaleString()} / 100,000</span>
              </div>
              <label className="mt-2 inline-flex min-h-9 cursor-pointer items-center gap-2 border border-white/10 px-3 text-xs text-[#c7ccc4] hover:border-[#92d6a4]/50 hover:text-white">
                <Upload size={14} />
                Upload .txt document
                <input type="file" accept=".txt,text/plain" className="sr-only" onChange={loadTextFile} />
              </label>
              {fileName && <span className="ml-2 text-xs text-[#929990]">{fileName}</span>}
              <textarea
                id="submission-text"
                required
                maxLength={100_000}
                value={text}
                onChange={(event) => {
                  setText(event.target.value);
                  setFileName("");
                }}
                placeholder="Paste citizen correspondence or a service request..."
                className="mt-2 min-h-56 w-full resize-y border border-white/10 bg-[#101311] p-4 text-sm leading-6 text-[#f1f2ed] outline-none placeholder:text-[#777e75] focus:border-[#92d6a4]"
              />

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="mr-1 text-[11px] text-[#838a81]">Try an example</span>
                {examples.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    onClick={() => loadExample(example)}
                    className="border border-white/10 px-2.5 py-1.5 text-[11px] text-[#c7ccc4] hover:border-[#92d6a4]/50 hover:text-white"
                  >
                    {example.label}
                  </button>
                ))}
              </div>

              {error && (
                <div role="alert" className="mt-4 flex items-start gap-2 border border-red-300/20 bg-red-300/5 p-3 text-xs leading-5 text-red-200">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-5">
                <p className="flex max-w-xs items-start gap-2 text-[11px] leading-4 text-[#929990]">
                  <LockKeyhole size={14} className="mt-0.5 shrink-0 text-[#a7d9b0]" />
                  PII is redacted before classification. Avoid submitting live personal data in this demo.
                </p>
                <button
                  type="submit"
                  disabled={loading || !text.trim()}
                  className="inline-flex min-h-11 items-center justify-center gap-2 bg-[#b9e6c0] px-4 text-sm font-semibold text-[#142018] hover:bg-[#d0f1d5] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? <LoaderCircle size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  {loading ? "Processing submission" : "Run triage"}
                </button>
              </div>
            </form>
          </section>

          <section className="border border-white/10 bg-[#171b18]" aria-live="polite">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center border border-white/10 bg-[#202621] text-[#a7d9b0]">
                  <Route size={16} />
                </span>
                <div>
                  <h2 className="text-sm font-semibold">Triage outcome</h2>
                  <p className="mt-0.5 text-xs text-[#929990]">Department recommendation and audit reference</p>
                </div>
              </div>
              <span className="font-mono text-xs text-[#929990]">02 / 02</span>
            </div>

            {loading ? (
              <div className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
                <LoaderCircle size={24} className="animate-spin text-[#a7d9b0]" />
                <p className="mt-4 text-sm font-medium">Running document triage</p>
                <p className="mt-2 max-w-xs text-xs leading-5 text-[#929990]">Sanitization, classification, and routing are handled by the CivicOs API.</p>
              </div>
            ) : result ? (
              <div className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className={`border px-2.5 py-1 text-xs font-medium ${result.status === "completed" ? "border-[#92d6a4]/30 bg-[#92d6a4]/10 text-[#b9e6c0]" : "border-amber-200/30 bg-amber-200/10 text-amber-100"}`}>
                    {result.status === "completed" ? "Triage complete" : `Status: ${result.status}`}
                  </span>
                  {decision && <span className={`border px-2.5 py-1 text-xs font-medium ${priorityClass(decision.priority)}`}>{decision.priority} priority</span>}
                </div>

                {decision ? (
                  <>
                    <p className="mt-5 text-xs text-[#929990]">Recommended department</p>
                    <h3 className="mt-1 text-2xl font-semibold">{decision.department}</h3>
                    <div className="mt-4 grid grid-cols-2 gap-3 border-y border-white/10 py-4">
                      <div>
                        <p className="text-[11px] text-[#929990]">Category</p>
                        <p className="mt-1 text-sm">{decision.category}</p>
                      </div>
                      <div>
                        <p className="text-[11px] text-[#929990]">Confidence</p>
                        <p className="mt-1 font-mono text-sm">{Math.round(decision.confidence * 100)}%</p>
                      </div>
                    </div>
                    <p className="mt-4 text-xs font-medium text-[#c7ccc4]">Summary</p>
                    <p className="mt-1 text-sm leading-6 text-[#e0e3dc]">{decision.summary}</p>
                    <p className="mt-4 text-xs font-medium text-[#c7ccc4]">Routing rationale</p>
                    <p className="mt-1 text-sm leading-6 text-[#a5aaa2]">{decision.decision_rationale}</p>
                    <p className="mt-5 text-xs font-medium text-[#c7ccc4]">Redacted document</p>
                    <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words border border-white/10 bg-[#101311] p-3 text-xs leading-5 text-[#c7ccc4]">
                      {result.redacted_text ?? "Redacted text is not available for this processing state."}
                    </pre>

                    {result.requires_review && (
                      <div className="mt-4 flex items-start gap-2 border border-amber-200/20 bg-amber-200/5 p-3 text-xs leading-5 text-amber-100">
                        <AlertCircle size={15} className="mt-0.5 shrink-0" />
                        This submission is flagged for staff review before action.
                      </div>
                    )}
                  </>
                ) : (
                  <div className="mt-5 border border-amber-200/20 bg-amber-200/5 p-4 text-sm leading-6 text-amber-100">
                    The API accepted this submission for asynchronous processing. A final classification was not included in its response.
                  </div>
                )}

                <div className="mt-5 border-t border-white/10 pt-4">
                  <div className="mb-3 flex items-center gap-2 text-xs font-medium text-[#c7ccc4]">
                    <ShieldCheck size={15} className="text-[#a7d9b0]" />
                    Processing record
                  </div>
                  <div className="grid grid-cols-2 gap-y-3 text-xs">
                    <span className="text-[#929990]">PII entities masked</span>
                    <span className="text-right font-mono">{result.pii_entities_masked}</span>
                    <span className="text-[#929990]">Created</span>
                    <span className="text-right font-mono">{new Date(result.created_at).toLocaleString()}</span>
                    <span className="text-[#929990]">Trace ID</span>
                    <span className="flex min-w-0 items-center justify-end gap-1.5 font-mono text-[10px] sm:text-xs">
                      <span className="truncate">{result.trace_id}</span>
                      <button type="button" onClick={copyTraceId} title="Copy trace ID" aria-label="Copy trace ID" className="shrink-0 p-1 text-[#a5aaa2] hover:text-white">
                        {copied ? <Check size={13} /> : <Clipboard size={13} />}
                      </button>
                    </span>
                    <span className="text-[#929990]">Audit entry hash</span>
                    <span className="break-all text-right font-mono text-[10px] sm:text-xs">{result.audit_hash ?? "Not recorded"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex min-h-72 flex-col items-center justify-center px-8 text-center">
                <span className="flex h-11 w-11 items-center justify-center border border-white/10 bg-[#202621] text-[#a7d9b0]">
                  <FileText size={19} />
                </span>
                <p className="mt-4 text-sm font-medium">No submission processed</p>
                <p className="mt-2 max-w-xs text-xs leading-5 text-[#929990]">Your department recommendation, review flag, and trace record will appear here.</p>
              </div>
            )}
          </section>
        </div>

        <div className="mt-5 grid gap-px border border-white/10 bg-white/10 sm:grid-cols-3">
          <div className="flex items-center gap-3 bg-[#141814] px-4 py-3">
            <LockKeyhole size={15} className="text-[#a7d9b0]" />
            <span className="text-xs text-[#c7ccc4]">PII redaction before classification</span>
          </div>
          <div className="flex items-center gap-3 bg-[#141814] px-4 py-3">
            <Route size={15} className="text-[#a7d9b0]" />
            <span className="text-xs text-[#c7ccc4]">Department-level routing recommendation</span>
          </div>
          <div className="flex items-center gap-3 bg-[#141814] px-4 py-3">
            <ShieldCheck size={15} className="text-[#a7d9b0]" />
            <span className="text-xs text-[#c7ccc4]">Traceable processing record</span>
          </div>
        </div>
      </div>
    </main>
  );
}