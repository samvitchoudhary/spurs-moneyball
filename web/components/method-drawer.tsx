import type { ReactNode } from "react";
import katex from "katex";

export function MethodDrawer({
  title = "How this works",
  formula,
  children,
}: {
  title?: string;
  formula?: string;
  children: ReactNode;
}) {
  const html = formula
    ? katex.renderToString(formula, { displayMode: true, throwOnError: false, output: "html" })
    : null;
  return (
    <details className="mt-6 max-w-2xl rounded-2xl border border-[#E4E0D6] bg-white px-4 py-3">
      <summary className="cursor-pointer font-medium text-[#132257]">{title}</summary>
      <div className="mt-3 space-y-3 text-sm leading-6 text-[#3A4256]">
        {html ? <div className="overflow-x-auto text-[#132257]" dangerouslySetInnerHTML={{ __html: html }} /> : null}
        {children}
      </div>
    </details>
  );
}
