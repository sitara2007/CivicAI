import { Database, FileCheck, Shield } from "lucide-react";
const items = [
  {
    icon: Shield,
    title: "PII Guard",
    description: "Redacts Aadhaar, PAN, phone, email before model sees data.",
  },
  {
    icon: Database,
    title: "RAG Pipeline",
    description: "Qdrant retrieval with chunk reranking. 94.2% accuracy.",
  },
  {
    icon: FileCheck,
    title: "Audit Trail",
    description: "Hash-chain logs. Every decision traceable. Compliance-ready.",
  },
];
export function Architecture() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="mb-12 text-2xl font-semibold text-[#EDEDED]">
        How it works
      </h2>
      <div className="grid gap-6 md:grid-cols-3">
        {items.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="rounded-lg border border-[#1F1F1F] bg-[#111111] p-6 hover:border-[#00D4AA]/30"
          >
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-md border border-[#1F1F1F] bg-[#0A0A0A] text-[#00D4AA]">
              <Icon size={18} />
            </div>
            <h3 className="text-xl font-semibold text-[#EDEDED]">{title}</h3>
            <p className="mt-3 text-sm leading-6 text-[#8A8A8A]">
              {description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
