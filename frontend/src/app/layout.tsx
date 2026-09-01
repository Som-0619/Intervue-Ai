import './globals.css';
import Link from 'next/link';
import { Terminal, ShieldCheck, Sparkles, LayoutDashboard } from 'lucide-react';

export const metadata = {
  title: 'IntervueAI — Role-Based Technical Interview Platform',
  description: 'Production-grade AI technical interview platform with calm, modern UX and RAG grounding.',
  icons: {
    icon: [
      { url: '/icon.png', type: 'image/png' },
      { url: '/favicon.ico', type: 'image/x-icon' },
    ],
    shortcut: '/favicon.ico',
    apple: '/apple-icon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full bg-[#fcfcfc] text-zinc-900 flex flex-col antialiased selection:bg-zinc-900 selection:text-white">
        {/* Navigation Bar */}
        <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 bg-white/80 backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-lg bg-zinc-900 text-white flex items-center justify-center p-1 shadow-sm overflow-hidden">
                <img src="/logo.png" alt="IntervueAI Logo" className="w-full h-full object-contain filter invert" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm tracking-tight text-zinc-900">
                  IntervueAI
                </span>
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                  v1.0
                </span>
              </div>
            </Link>

            <nav className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-xs font-medium transition-all"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </Link>

              <Link
                href="/setup"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition-all shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Start Interview</span>
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-200 bg-white py-6">
          <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
            <div className="flex items-center gap-2 font-mono">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>IntervueAI Technical Engine — RAG Grounded</span>
            </div>
            <div>
              Built with Love and Tokens...
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
