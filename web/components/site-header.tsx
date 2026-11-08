"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CommandPalette } from "@/components/command-palette";

const LINKS = [
  ["Similarity", "/similarity"],
  ["Styles", "/styles"],
  ["Value", "/value"],
  ["Backtest", "/backtest"],
  ["Needs", "/needs"],
  ["Shortlist", "/shortlist"],
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-[#E4E0D6] bg-[#FAFAF7]/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-5">
        <Link href="/" className="font-serif text-lg text-[#132257]">
          Spurs Moneyball
        </Link>
        <nav className="ml-auto hidden items-center gap-4 text-sm text-[#3A4256] md:flex" aria-label="Pages">
          {LINKS.map(([label, href]) => (
            <Link key={href} href={href} className="hover:text-[#132257]">
              {label}
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="ml-auto rounded-full border border-[#E4E0D6] bg-white px-3 py-1.5 text-sm text-[#132257] md:ml-0"
          onClick={() => setOpen(true)}
        >
          Search <span className="text-[#5C471C]">⌘K</span>
        </button>
        <button
          type="button"
          className="rounded-full border border-[#E4E0D6] px-3 py-1.5 text-sm text-[#132257] md:hidden"
          aria-expanded={menu}
          onClick={() => setMenu((value) => !value)}
        >
          Menu
        </button>
      </div>
      {menu ? (
        <nav className="border-t border-[#E4E0D6] px-5 py-3 md:hidden" aria-label="Pages">
          <ul className="grid grid-cols-2 gap-2 text-sm">
            {LINKS.map(([label, href]) => (
              <li key={href}>
                <Link href={href} className="block rounded-lg px-2 py-2 text-[#132257]" onClick={() => setMenu(false)}>
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
      <CommandPalette open={open} onOpenChange={setOpen} />
    </header>
  );
}
