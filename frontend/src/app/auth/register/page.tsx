"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowRight, FlaskConical, UserPlus } from "lucide-react";

import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../components/ui/card";
import { BrandHeroArt } from "../../../components/brand-hero-art";
import { getApiErrorMessage, registerUser } from "../../../lib/api";
import { enterGuestMode, isAuthClient, isGuestClient } from "../../../lib/auth";

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const hasAuth = isAuthClient();
    const hasGuest = isGuestClient();
    if (hasGuest || hasAuth) {
      window.location.replace("/dashboard");
    }
  }, []);

  const validate = () => {
    if (!emailRegex.test(email)) {
      toast.error("Enter a valid email address.");
      return false;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return false;
    }
    if (password !== confirm) {
      toast.error("Passwords do not match.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      await registerUser(email, password);
      toast.success("Account created. You can now log in.");
      window.location.href = "/auth/login";
    } catch (error: unknown) {
      toast.error("Registration failed", {
        description: getApiErrorMessage(error)
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-animate="fade-up">
      <header className="rounded-3xl border border-slate-200/80 bg-white/90 p-7 shadow-[0_20px_42px_-28px_rgba(15,76,92,0.45)]">
        <p className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-800">
          <FlaskConical className="h-3.5 w-3.5" />
          Research demo - not a medical device
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl" style={{ fontFamily: "var(--font-display)" }}>
          Create Your Account
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600 sm:text-base">
          Register for full access to uploads, study processing, report exports, and history tracking.
        </p>
        <div className="mt-4 hidden sm:block">
          <BrandHeroArt className="h-20 w-32" />
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2" data-animate="fade-up-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="tx-icon text-primary" />
              Registration
            </CardTitle>
            <CardDescription>One account per user. Passwords are stored as secure hashes.</CardDescription>
          </CardHeader>

          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
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
                  autoComplete="new-password"
                  required
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm text-slate-700">
                Confirm Password
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.currentTarget.value)}
                  maxLength={72}
                  className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-900 transition placeholder:text-slate-400 focus:border-primary focus:outline-none"
                  placeholder="Re-enter password"
                  autoComplete="new-password"
                  required
                />
              </label>

              <Button type="submit" disabled={submitting} className="w-full justify-between">
                {submitting ? "Creating account..." : "Create Account"}
                <ArrowRight className="tx-icon" />
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Need Demo-Only Access?</CardTitle>
            <CardDescription>Use guest mode for UI exploration without persisted data.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-slate-700">
            <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3">
              <p>Guest mode keeps the environment low-risk for walkthroughs.</p>
              <p>Uploads, report exports, and history are intentionally disabled.</p>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                enterGuestMode();
                window.location.href = "/dashboard";
              }}
              className="w-full"
            >
              Continue as Guest
            </Button>
            <p className="text-sm text-slate-600">
              Already registered?{" "}
              <Link href="/auth/login" className="font-semibold text-primary">
                Sign in
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
