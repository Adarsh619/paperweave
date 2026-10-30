import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PaperWeave: see how AI research connects",
  description:
    "An agentic GraphRAG research assistant for AI/LLM papers. Ask a question and get a cited answer plus the knowledge graph behind it.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
              <span aria-hidden className="inline-block h-5 w-5 rounded-md bg-accent" />
              PaperWeave
            </Link>
            <a
              href="https://github.com/Adarsh619/paperweave"
              className="text-sm text-muted hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-border py-6 text-center text-xs text-muted">
          500 AI/LLM papers · Neo4j knowledge graph · Qdrant hybrid search · LangGraph agent · data from
          arXiv and Semantic Scholar
        </footer>
      </body>
    </html>
  );
}
