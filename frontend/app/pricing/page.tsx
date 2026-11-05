const tiers = [
  { name: "Free", price: "₹0", docs: "100 docs/month", cta: "Start free" },
  {
    name: "Starter",
    price: "₹8K",
    docs: "1,000 docs/month",
    cta: "Choose Starter",
  },
  { name: "Pro", price: "₹25K", docs: "10,000 docs/month", cta: "Choose Pro" },
];
export default function PricingPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-20">
      <h1 className="text-center text-4xl font-semibold tracking-tight text-[#EDEDED]">
        Pricing
      </h1>
      <div className="mt-16 grid gap-6 md:grid-cols-3">
        {tiers.map((t) => (
          <div
            key={t.name}
            className="rounded-lg border border-[#1F1F1F] bg-[#111111] p-6"
          >
            <h2 className="text-lg font-semibold text-[#EDEDED]">{t.name}</h2>
            <p className="mt-4 text-4xl font-semibold tracking-tight text-[#EDEDED]">
              {t.price}
            </p>
            <p className="mt-2 text-sm text-[#8A8A8A]">{t.docs}</p>
            <button className="mt-8 w-full rounded-md bg-[#00D4AA] py-3 text-sm font-medium text-black hover:bg-[#2BE6BC]">
              {t.cta}
            </button>
          </div>
        ))}
      </div>
    </main>
  );
}
