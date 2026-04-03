import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Providers } from "@/components/Providers";

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
      <body className="min-h-screen flex bg-[var(--color-bg-primary)]">
        <Providers>
          <Sidebar />
          <main className="flex-1 ml-60 p-7 overflow-auto min-h-screen">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
