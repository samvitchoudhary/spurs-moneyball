"use client";

import type { ComponentProps } from "react";
import { Command as CommandPrimitive } from "cmdk";

import { cn } from "@/lib/utils";

export function Command({ className, ...props }: ComponentProps<typeof CommandPrimitive>) {
  return <CommandPrimitive className={cn("flex h-full w-full flex-col", className)} {...props} />;
}

export function CommandInput({ className, ...props }: ComponentProps<typeof CommandPrimitive.Input>) {
  return (
    <CommandPrimitive.Input
      className={cn(
        "h-12 w-full border-b border-[#E4E0D6] bg-transparent px-4 text-base text-[#1C2333] outline-none placeholder:text-[#6B7280]",
        className,
      )}
      {...props}
    />
  );
}

export function CommandList({ className, ...props }: ComponentProps<typeof CommandPrimitive.List>) {
  return <CommandPrimitive.List className={cn("max-h-80 overflow-y-auto p-2", className)} {...props} />;
}

export function CommandEmpty(props: ComponentProps<typeof CommandPrimitive.Empty>) {
  return <CommandPrimitive.Empty className="px-3 py-6 text-sm text-[#3A4256]" {...props} />;
}

export function CommandItem({ className, ...props }: ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      className={cn(
        "flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 text-sm aria-selected:bg-[#F3EFE6]",
        className,
      )}
      {...props}
    />
  );
}
