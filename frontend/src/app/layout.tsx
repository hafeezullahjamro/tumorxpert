import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { Manrope, Source_Serif_4 } from "next/font/google";

import "./globals.css";
import { AuthActions } from "../components/auth-actions";
import { Providers } from "../components/providers";

export const metadata: Metadata = {
  title: "TumorXpert",
  description: "Local-first brain tumor MRI workflow with modality synthesis and segmentation."
};

const uiFont = Manrope({ subsets: ["latin"], variable: "--font-ui" });
const displayFont = Source_Serif_4({ subsets: ["latin"], variable: "--font-display", weight: ["600", "700"] });

const navLinks = {
  authed: [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/upload", label: "Upload" },
    { href: "/studies", label: "Studies" },
    { href: "/compare", label: "Compare" },
    { href: "/jobs", label: "Jobs" },
    { href: "/admin", label: "Admin" },
    { href: "/settings", label: "Settings" },
    { href: "/help", label: "Help" }
  ],
  guest: [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/studies", label: "Studies" },
    { href: "/compare", label: "Compare" },
    { href: "/help", label: "Help" }
  ]
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = cookies();
  const hasAuth = cookieStore.get("tx_auth")?.value === "1";
  const hasGuest = cookieStore.get("tx_guest")?.value === "1";
  const homeHref = hasAuth || hasGuest ? "/dashboard" : "/auth/login";
  const activeLinks = hasAuth ? navLinks.authed : hasGuest ? navLinks.guest : [];

  return (
    <html lang="en" className={`${uiFont.variable} ${displayFont.variable}`}>
      <body>
        <Providers isGuest={hasGuest}>
          <div className="relative min-h-screen overflow-hidden">
            <div aria-hidden className="pointer-events-none absolute inset-0">
              <div className="absolute -left-24 top-8 h-72 w-72 rounded-full bg-[#b7d8d3]/45 blur-3xl" />
              <div className="absolute right-0 top-24 h-80 w-80 rounded-full bg-[#c0dbe4]/35 blur-3xl" />
            </div>

            <header className="relative border-b border-slate-200/80 bg-white/70 backdrop-blur-xl">
              <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between gap-3">
                  <Link href={homeHref} className="inline-flex items-center gap-2">
                    <span className="rounded-lg bg-primary px-2 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-white">
                      TX
                    </span>
                    <span className="text-xl font-semibold tracking-tight text-slate-900" style={{ fontFamily: "var(--font-display)" }}>
                      TumorXpert
                    </span>
                  </Link>
                  <AuthActions />
                </div>

                {(hasAuth || hasGuest) && (
                  <nav className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700" aria-label="Primary">
                    {activeLinks.map((link) => (
                      <Link
                        key={link.href}
                        href={link.href}
                        className="rounded-full border border-slate-200 bg-white/85 px-3.5 py-1.5 transition hover:border-slate-300 hover:bg-white"
                      >
                        {link.label}
                      </Link>
                    ))}
                  </nav>
                )}
              </div>
            </header>

            {hasGuest && (
              <div className="relative border-b border-amber-200/90 bg-amber-50/95 px-4 py-2 text-center text-xs text-amber-800">
                Guest mode active: uploads, exports, and saved history are disabled.
              </div>
            )}

            <main className="relative mx-auto w-full max-w-6xl px-4 pb-14 pt-10 sm:px-6 lg:px-8">{children}</main>

            <footer className="relative border-t border-slate-200/80 bg-white/70 py-6 text-center text-xs text-slate-600 backdrop-blur">
              Research demo only. Not for clinical use.
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
