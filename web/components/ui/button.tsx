import * as React from "react";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/lib/utils";

export function Button({
  className,
  asChild = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full border border-[#E4E0D6] bg-white px-3 py-1.5 text-sm text-[#132257] transition-colors hover:bg-[#F3EFE6]",
        className,
      )}
      {...props}
    />
  );
}
