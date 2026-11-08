import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";
import "katex/dist/katex.min.css";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

export const metadata: Metadata = {
  title: { default: "Spurs Moneyball", template: "%s · Spurs Moneyball" },
  description: "A data story about finding players whose stats fit what Tottenham needs.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${fraunces.variable} font-sans antialiased`}>
        <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-3 focus:py-2">
          Skip to content
        </a>
        <SiteHeader />
        <main id="content">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
