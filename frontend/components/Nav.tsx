"use client";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useState } from "react";

const links = [
  { href: "/docs", label: "Docs" },
  { href: "/pricing", label: "Pricing" },
  {
    href: "https://github.com/sitara2007/CivicOs",
    label: "GitHub",
    external: true,
  },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-[#1F1F1F] bg-[#0A0A0A]/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-[#EDEDED]"
        >
          CivicOs
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {links.map((l) =>
            l.external ? (
              <a
                key={l.label}
                href={l.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-[#8A8A8A] hover:text-[#EDEDED]"
              >
                {l.label}
              </a>
            ) : (
              <Link
                key={l.label}
                href={l.href}
                className="text-sm text-[#8A8A8A] hover:text-[#EDEDED]"
              >
                {l.label}
              </Link>
            ),
          )}
        </nav>
        <Link
          href="/docs"
          className="hidden rounded-md bg-[#00D4AA] px-4 py-2 text-sm font-medium text-black md:inline-flex hover:shadow-[0_0_24px_rgba(0,212,170,0.45)]"
        >
          Try Demo
        </Link>
        <button
          onClick={() => setOpen(!open)}
          className="rounded-md border border-[#1F1F1F] bg-[#111111] p-2 text-[#EDEDED] md:hidden"
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>
      {open && (
        <div className="border-t border-[#1F1F1F] bg-[#0A0A0A] md:hidden">
          <nav className="flex flex-col gap-4 px-6 py-5">
            {links.map((l) =>
              l.external ? (
                <a
                  key={l.label}
                  href={l.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-[#8A8A8A]"
                >
                  {l.label}
                </a>
              ) : (
                <Link
                  key={l.label}
                  href={l.href}
                  className="text-sm text-[#8A8A8A]"
                >
                  {l.label}
                </Link>
              ),
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
