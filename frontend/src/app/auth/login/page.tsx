"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowRight, FlaskConical, ShieldCheck } from "lucide-react";

import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../components/ui/card";
import { BrandHeroArt } from "../../../components/brand-hero-art";
import { getApiErrorMessage, loginUser } from "../../../lib/api";
import { enterGuestMode, getLoginRedirect, isAuthClient, isGuestClient } from "../../../lib/auth";

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lockMessage, setLockMessage] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const hasAuth = isAuthClient();
    const hasGuest = isGuestClient();
    if (hasGuest) {
      window.location.replace("/dashboard");
      return;
    }
    if (hasAuth) {
      window.location.replace(getLoginRedirect());
    }
  }, []);

  useEffect(() => {
    if (!lockMessage) return;
    const timeout = window.setTimeout(() => {
      setLockMessage(null);
      setAttempts(0);
    }, 60000);
    return () => window.clearTimeout(timeout);
  }, [lockMessage]);

  const validate = () => {
    if (!emailRegex.test(email)) {
      toast.error("Enter a valid email address.");
      return false;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return false;
    }
    return true;
  };

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) return;
    if (lockMessage) {
      toast.error(lockMessage);
      return;
    }

    setIsSubmitting(true);
    try {
      await loginUser(email, password);
      document.cookie = "tx_auth=1; path=/; SameSite=Lax; Max-Age=28800";
      document.cookie = "tx_guest=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      toast.success("Login successful");
      window.location.href = getLoginRedirect();
    } catch (error: unknown) {
      const nextAttempts = attempts + 1;
      setAttempts(nextAttempts);
      if (nextAttempts >= 5) {
        setLockMessage("Too many failed attempts. Please wait one minute before retrying.");
      }
      toast.error("Login failed", {
        description: getApiErrorMessage(error)
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGuest = () => {
    toast.info("Guest mode: no uploads, no exports, and no saved study history.");
    enterGuestMode();
    window.location.href = "/dashboard";
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-animate="fade-up">
      <header className="rounded-3xl border border-slate-200/80 bg-white/90 p-7 shadow-[0_20px_42px_-28px_rgba(15,76,92,0.45)]">
        <p className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-800">
          <FlaskConical className="h-3.5 w-3.5" />
          Research demo - not a medical device
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl" style={{ fontFamily: "var(--font-display)" }}>
          Sign In to TumorXpert
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600 sm:text-base">
          Access full study workflows with your account. Guest mode is available for interface walkthroughs only.
        </p>
        <div className="mt-4 hidden sm:block">
          <BrandHeroArt className="h-20 w-32" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2" data-animate="fade-up-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="tx-icon text-primary" />
              Authenticated Access
            </CardTitle>
            <CardDescription>Use your credentials for uploads, processing, and report exports.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleLogin}>
              <label className="flex flex-col gap-1.5 text-sm text-slate-700">
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                  className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-900 transition placeholder:text-slate-400 focus:border-primary focus:outline-none"
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm text-slate-700">
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.currentTarget.value)}
                  maxLength={72}
                  className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-900 transition placeholder:text-slate-400 focus:border-primary focus:outline-none"
                  placeholder="At least 8 characters"
                  autoComplete="current-password"
                  required
                />
              </label>

              <div aria-live="polite" className="min-h-5 text-sm text-rose-700">
                {lockMessage}
              </div>

              <Button type="submit" disabled={isSubmitting || Boolean(lockMessage)} className="w-full justify-between">
                {isSubmitting ? "Signing in..." : "Sign In"}
                <ArrowRight className="tx-icon" />
              </Button>

              <p className="text-xs text-slate-500">
                Research-use environment. Do not upload real patient data without approved governance.
              </p>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Guest Access</CardTitle>
            <CardDescription>Explore UI flows without creating an account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
              <p>Guest mode is useful for demos and onboarding.</p>
              <p>Uploads, exports, and persistent history remain disabled.</p>
            </div>

            <Button type="button" variant="secondary" onClick={handleGuest} className="w-full">
              Continue as Guest
            </Button>

            <p className="text-sm text-slate-600">
              Need an account?{" "}
              <Link href="/auth/register" className="font-semibold text-primary">
                Create one here
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
