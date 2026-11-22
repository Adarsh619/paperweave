import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import { MotionProvider } from "@/components/Motion";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Serif for headings: the "research journal" voice.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PaperWeave: see how research connects",
  description:
    "An agentic GraphRAG research assistant for AI, computer science and physics papers. Ask a question and get a cited answer plus the knowledge graph behind it.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <MotionProvider>
          <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
              <Link href="/" className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
                {/* Three woven strands: the PaperWeave mark. */}
                <svg aria-hidden viewBox="0 0 24 24" className="h-5 w-5 text-accent" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                  <path d="M3 7c4 0 5 10 9 10s5-10 9-10" />
                  <path d="M3 17c4 0 5-10 9-10s5 10 9 10" opacity="0.55" />
                  <path d="M3 12h18" opacity="0.3" />
                </svg>
                PaperWeave
              </Link>
              <nav className="flex items-center gap-3 whitespace-nowrap text-[13px] text-muted sm:gap-5 sm:text-sm">
                <Link href="/trends" className="hover:text-foreground">
                  Trends
                </Link>
                <Link href="/how-it-works" className="hover:text-foreground">
                  How it works
                </Link>
                <Link href="/about" className="hover:text-foreground">
                  About
                </Link>
                <a
                  href="https://github.com/Adarsh619/paperweave"
                  className="hidden hover:text-foreground sm:inline"
                  target="_blank"
                  rel="noreferrer"
                >
                  GitHub
                </a>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-border py-6 text-center text-xs text-muted">
            Neo4j knowledge graph · Qdrant hybrid search · LangGraph agent · data from arXiv and Semantic Scholar
          </footer>
        </MotionProvider>
      </body>
    </html>
  );
}
