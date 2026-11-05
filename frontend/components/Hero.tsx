"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export function Hero() {
  const [status, setStatus] = useState<"online" | "down" | "loading">(
    "loading",
  );
  useEffect(() => {
    let mounted = true;
    fetch("https://civicai-backend-hb5e.onrender.com/health")
      .then((r) => mounted && setStatus(r.ok ? "online" : "down"))
      .catch(() => mounted && setStatus("down"));
    return () => {
      mounted = false;
    };
  }, []);
  const dot =
    status === "online"
      ? "bg-[#00D4AA]"
      : status === "down"
        ? "bg-red-500"
        : "bg-yellow-500";
  const label =
    status === "online"
      ? "API: Operational"
      : status === "down"
        ? "API: Down"
        : "API: Checking";
  return (
    <section className="relative mx-auto max-w-6xl px-6 pb-24 pt-32">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_center,rgba(124,58,237,0.14),transparent_28%),radial-gradient(circle_at_top,rgba(0,212,170,0.10),transparent_40%)]" />
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto max-w-4xl text-center"
      >
        <div className="mb-8 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-md border border-[#1F1F1F] bg-[#111111] px-3 py-2 text-xs text-[#EDEDED]">
            <span className={`h-2 w-2 rounded-full ${dot}`} />
            {label}
          </div>
        </div>
        <h1 className="text-6xl font-semibold leading-[1.05] tracking-tight text-[#EDEDED] md:text-7xl">
          AI Document Triage for Government
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-[#8A8A8A]">
          PII redaction + hash-chain audit + hallucination scoring. Built on Go
          + ClickHouse.
        </p>
        <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
          <Link
            href="/docs"
            className="inline-flex items-center justify-center rounded-md bg-[#00D4AA] px-5 py-3 text-sm font-medium text-black hover:bg-[#2BE6BC]"
          >
            View Live Demo
          </Link>
          <Link
            href="/docs"
            className="inline-flex items-center justify-center rounded-md border border-[#1F1F1F] px-5 py-3 text-sm font-medium text-[#EDEDED] hover:bg-white/5"
          >
            Read Docs
          </Link>
        </div>
      </motion.div>
    </section>
  );
}
