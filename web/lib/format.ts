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

/** Same rule as the January shortlist when date of birth is missing. */
export function ageOnJan2027(birthYear: number): number {
  return 2027 - 1 - birthYear;
}

function ageOnDate(birthDate: Date, on: Date): number {
  let age = on.getFullYear() - birthDate.getFullYear();
  const monthDay = (on.getMonth() + 1) * 100 + on.getDate();
  const birthMonthDay = (birthDate.getMonth() + 1) * 100 + birthDate.getDate();
  if (monthDay < birthMonthDay) age -= 1;
  return age;
}

/** Current-squad copy on the needs page: window age from birth year, or calendar age from a full birth date. */
export function squadMentionAge(player: {
  birthYear: number | null;
  age: number | null;
  birthDate?: string | null;
}): string {
  if (player.birthDate) {
    const born = new Date(player.birthDate);
    if (!Number.isNaN(born.getTime())) return formatAge(ageOnDate(born, new Date()));
  }
  if (player.birthYear != null) return `${ageOnJan2027(player.birthYear)}, age on 1 Jan 2027`;
  return formatAge(player.age);
}

export function formatSimilarity(value: number): string {
  return `${Math.round(value * 100)}%`;
}
