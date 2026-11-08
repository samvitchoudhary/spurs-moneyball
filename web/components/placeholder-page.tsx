import Link from "next/link";

export function PlaceholderPage({ eyebrow, title, dek }: { eyebrow: string; title: string; dek: string }) {
  return (
    <article className="mx-auto max-w-2xl px-5 py-16">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#5C471C]">{eyebrow}</p>
      <h1 className="mt-2 font-serif text-4xl text-[#132257]">{title}</h1>
      <p className="mt-4 text-lg leading-relaxed text-[#3A4256]">{dek}</p>
      <p className="mt-6 text-sm text-[#3A4256]">This page is a placeholder. The full version comes in a later pass.</p>
      <Link href="/" className="mt-6 inline-block text-[#132257] underline">
        Back to the story
      </Link>
    </article>
  );
}
