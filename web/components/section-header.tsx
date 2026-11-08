export function SectionHeader({ eyebrow, title, dek }: { eyebrow: string; title: string; dek: string }) {
  return (
    <header className="max-w-2xl">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#5C471C]">{eyebrow}</p>
      <h2 className="mt-2 font-serif text-3xl leading-tight text-[#132257] sm:text-4xl">{title}</h2>
      <p className="mt-3 text-lg leading-relaxed text-[#3A4256]">{dek}</p>
    </header>
  );
}
