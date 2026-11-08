import { initials, positionColor } from "@/lib/positions";

export function PlayerAvatar({ name, positionGroup, size = 40 }: { name: string; positionGroup?: string | null; size?: number }) {
  return (
    <span
      aria-hidden
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{ width: size, height: size, background: positionColor(positionGroup), fontSize: size < 36 ? 11 : 13 }}
    >
      {initials(name)}
    </span>
  );
}
