import type { Metadata } from "next";
import { Fraunces, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";
import { PlayerBanner } from "@/components/player-banner";
import { Providers } from "@/components/providers";
import { ScrollReveal } from "@/components/scroll-reveal";
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
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Operation Noel",
    template: "%s | Operation Noel",
  },
  description: "Jeu logistique du Pere Noel: planifie tes tournees, bats l'IA et optimise ton score.",
  openGraph: {
    title: "Operation Noel",
    description: "Planifie des tournees, compare toi a l'IA et progresse en campagne.",
    url: "/",
    siteName: "Operation Noel",
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Operation Noel",
    description: "Planifie des tournees et bats l'IA.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body className={`${bodyFont.variable} ${displayFont.variable}`}>
        <Providers>
          <ScrollReveal />
          <PlayerBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
