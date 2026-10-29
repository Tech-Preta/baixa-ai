import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import { SentryInit } from "./components/sentry-init";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://baixa.nataliagranato.xyz"),
  title: "Baixa.ai — baixar mídia pública",
  description:
    "Cole um link do Instagram, TikTok ou X e baixe fotos e vídeos públicos. Grátis, sem anúncios e sem login.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${outfit.variable} ${fraunces.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans text-ink">
        <SentryInit />
        {children}
      </body>
    </html>
  );
}
