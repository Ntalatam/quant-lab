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
      <body className="min-h-screen flex overflow-x-hidden bg-[var(--color-bg-primary)]">
        <Providers>
          <Sidebar />
          <main className="relative flex-1 min-h-screen overflow-x-hidden lg:ml-64">
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "linear-gradient(180deg, rgba(255,255,255,0.018) 0%, transparent 18%)",
              }}
            />
            <div className="relative mx-auto min-h-screen w-full max-w-[1660px] px-4 pb-8 pt-16 lg:px-8 lg:pb-12 lg:pt-8">
              {children}
            </div>
          </main>
        </Providers>
      </body>
    </html>
  );
}
