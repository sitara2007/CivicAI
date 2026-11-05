import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { Architecture } from "@/components/Architecture";
import { Benchmarks } from "@/components/Benchmarks";
import { LiveDemo } from "@/components/LiveDemo";
import { Footer } from "@/components/Footer";
export default function HomePage() {
  return (
    <main className="min-h-screen">
      <Nav />
      <Hero />
      <Architecture />
      <Benchmarks />
      <LiveDemo />
      <Footer />
    </main>
  );
}
