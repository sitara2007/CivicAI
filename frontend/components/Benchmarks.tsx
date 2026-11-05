const rows = [
  { label: "p99 latency", value: "< 50ms" },
  { label: "Throughput", value: "12K events/sec" },
  { label: "Classification accuracy", value: "94.2%" },
];
export function Benchmarks() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <p className="mb-8 text-xs uppercase tracking-[0.22em] text-[#8A8A8A]">
        Benchmarks
      </p>
      <div className="overflow-hidden rounded-lg border border-[#1F1F1F] bg-[#111111]">
        <table className="w-full border-collapse text-left text-sm">
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.label}
                className="border-b border-[#1F1F1F] last:border-b-0"
              >
                <td className="px-5 py-4 text-[#EDEDED]">{r.label}</td>
                <td className="px-5 py-4 text-right font-mono text-[#00D4AA]">
                  {r.value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
