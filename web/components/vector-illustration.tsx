"use client";

import { motion, useReducedMotion } from "framer-motion";

const STATS = [
  ["Shots", 0.4],
  ["Tackles", 0.85],
  ["Crosses", 0.2],
  ["Passes", 0.7],
];

export function VectorIllustration() {
  const reduce = useReducedMotion();
  return (
    <div className="grid items-center gap-6 rounded-2xl border border-[#E4E0D6] bg-white p-5 sm:grid-cols-[1fr_auto_1fr]">
      <ul className="space-y-3">
        {STATS.map(([label, amount], index) => (
          <li key={label}>
            <div className="mb-1 text-sm text-[#3A4256]">{label}</div>
            <div className="h-1.5 rounded-full bg-[#E7E4DC]">
              <motion.div
                className="h-full rounded-full bg-[#132257]"
                initial={reduce ? false : { width: 0 }}
                whileInView={{ width: `${Number(amount) * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.08 }}
              />
            </div>
          </li>
        ))}
      </ul>
      <div className="hidden text-2xl text-[#9A7B3C] sm:block" aria-hidden>
        →
      </div>
      <p className="font-serif text-2xl leading-snug text-[#132257]">
        [0.4, 0.9, 0.2, 0.7]
        <span className="mt-2 block font-sans text-sm text-[#3A4256]">One number per stat, on the same scale.</span>
      </p>
    </div>
  );
}
