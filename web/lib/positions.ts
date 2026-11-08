/** Muted, distinct, and dark enough for white initials. The same map is used on every page. */
export const POSITION_COLOR: Record<string, string> = {
  CB: "#3D5A80",
  FB: "#1F6F5B",
  CM: "#A15C12",
  AM_W: "#6E4C7A",
  ST: "#9A3E32",
  GK: "#5E656B",
};

export function positionColor(group: string | null | undefined): string {
  if (!group) return "#5E656B";
  return POSITION_COLOR[group] ?? "#5E656B";
}

export function initials(name: string): string {
  const parts = name.replace(/-/g, " ").split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
