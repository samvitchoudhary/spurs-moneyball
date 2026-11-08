import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";

export function PlayerChip({
  id,
  name,
  positionGroup,
}: {
  id?: string | null;
  name: string;
  positionGroup?: string | null;
}) {
  const body = (
    <span className="inline-flex items-center gap-2">
      <PlayerAvatar name={name} positionGroup={positionGroup} size={22} />
      <span className="font-medium text-[#132257]">{name}</span>
    </span>
  );
  if (!id) return body;
  return (
    <Link href={`/player?id=${id}`} className="rounded-full hover:underline">
      {body}
    </Link>
  );
}
