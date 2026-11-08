"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { PlayerAvatar } from "@/components/player-avatar";
import type { SearchHit } from "@/lib/types";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const [players, setPlayers] = useState<SearchHit[]>([]);

  useEffect(() => {
    if (!open || players.length) return;
    fetch("/data/search.json")
      .then((response) => response.json())
      .then((data: SearchHit[]) => setPlayers(data))
      .catch(() => setPlayers([]));
  }, [open, players.length]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogTitle className="sr-only">Search players</DialogTitle>
        <Command label="Search players">
          <CommandInput placeholder="Search a player" autoFocus />
          <CommandList>
            <CommandEmpty>{players.length ? "No player matches." : "Loading players…"}</CommandEmpty>
            {players.map((player) => (
              <CommandItem
                key={player.id}
                value={`${player.name} ${player.team} ${player.position}`}
                onSelect={() => {
                  onOpenChange(false);
                  router.push(`/player/${player.id}`);
                }}
              >
                <PlayerAvatar name={player.name} positionGroup={player.positionGroup} size={28} />
                <span>
                  <span className="block text-[#132257]">{player.name}</span>
                  <span className="text-xs text-[#3A4256]">
                    {player.team} · {player.position}
                  </span>
                </span>
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
