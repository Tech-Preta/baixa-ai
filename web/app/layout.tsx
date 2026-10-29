import type { Metadata } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { SentryInit } from "./components/sentry-init";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://baixa.nataliagranato.xyz"),
  title: "Baixa.ai — baixar mídia pública",
  description:
    "Cole um link do Instagram, TikTok, X ou YouTube e baixe fotos, vídeos e MP3. Grátis, sem anúncios e sem login.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background font-sans text-foreground">
        <SentryInit />
        {children}
      </body>
    </html>
  );
}
