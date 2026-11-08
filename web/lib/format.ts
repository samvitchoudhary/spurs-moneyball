export function formatEuro(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "−" : "";
  const number = Math.abs(value);
  if (number >= 1_000_000) return `${sign}€${(number / 1_000_000).toFixed(1)}m`;
  if (number >= 1_000) return `${sign}€${Math.round(number / 1_000)}k`;
  return `${sign}€${Math.round(number)}`;
}

export function formatSignedPercent(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "—";
  const text = `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
  return text.replace("-", "−");
}

export function formatPercentile(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value)}`;
}

export function formatAge(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return String(Math.round(value));
}

export function formatSimilarity(value: number): string {
  return `${Math.round(value * 100)}%`;
}
