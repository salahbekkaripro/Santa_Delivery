import type { Metadata } from "next";
import { Fraunces, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";
import { PlayerBanner } from "@/components/player-banner";
import { Providers } from "@/components/providers";
import "./globals.css";

const bodyFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
});

const displayFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "Operation Noel",
  description: "Frontend Next.js pour la logistique du Pere Noel"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body className={`${bodyFont.variable} ${displayFont.variable}`}>
        <Providers>
          <PlayerBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
