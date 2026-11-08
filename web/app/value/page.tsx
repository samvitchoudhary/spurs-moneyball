import { PlaceholderPage } from "@/components/placeholder-page";

export const metadata = { title: "Value" };

export default function Page() {
  return (
    <PlaceholderPage
      eyebrow="What the fee should be"
      title="Value model"
      dek="A model of market value, then a correction for the way cheap fees are over-predicted."
    />
  );
}
