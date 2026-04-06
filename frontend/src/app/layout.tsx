import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { AppChrome } from "@/components/layout/AppChrome";

export const metadata: Metadata = {
  title: "QuantLab",
  description: "Quantitative research and backtesting platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-screen flex overflow-x-hidden bg-[var(--color-bg-primary)]">
        <Providers>
          <AppChrome>{children}</AppChrome>
        </Providers>
      </body>
    </html>
  );
}
