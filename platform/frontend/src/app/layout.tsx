import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/QueryProvider";
import { TopNav } from "@/components/layout/TopNav";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "APEX SDLC Platform",
  description: "Enterprise AI-powered SDLC operating system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <QueryProvider>
          <TopNav />
          <main className="min-h-screen bg-gray-50 pt-14">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
