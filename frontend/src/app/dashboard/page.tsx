"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowRight, FolderKanban, GaugeCircle, Layers3, ShieldAlert, UploadCloud } from "lucide-react";

import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { BrandHeroArt } from "../../components/brand-hero-art";
import { fetchHealth } from "../../lib/api";
import { useGuestMode } from "../../lib/auth";

export default function DashboardPage() {
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30000
  });
  const isGuest = useGuestMode();

  return (
    <div className="space-y-8">
      <section
        data-animate="fade-up"
        className="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-7 shadow-[0_24px_48px_-32px_rgba(15,76,92,0.45)]"
      >
        <div aria-hidden className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/55 blur-2xl" />
        <div className="relative grid gap-6 md:grid-cols-[1fr_auto] md:items-start">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-800">
              <ShieldAlert className="h-3.5 w-3.5" />
              Research demo - not a medical device
            </p>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl" style={{ fontFamily: "var(--font-display)" }}>
              Workflow Command Center
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
              Run multi-modality uploads, review segmentation outputs, and compare longitudinal changes from one dashboard. The backend completes a single missing modality with synthesis before segmentation when needed.
            </p>
            <div className="mt-4 hidden sm:block">
              <BrandHeroArt className="h-24 w-40" />
            </div>
          </div>

          <div className="grid min-w-[220px] gap-3">
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Backend Status</p>
              <p className={`mt-1 text-sm font-semibold ${data?.status === "ok" ? "text-emerald-700" : "text-amber-700"}`}>
                {data?.status === "ok" ? "Online" : isError ? "Offline" : "Checking..."}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Mode</p>
              <p className="mt-1 text-sm font-semibold text-slate-800">{isGuest ? "Guest (limited)" : "Authenticated"}</p>
            </div>
          </div>
        </div>
      </section>

      {isGuest && (
        <div
          data-animate="fade-up-2"
          className="rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-800"
        >
          Guest mode is active. Upload, export, and saved history features are disabled.
        </div>
      )}

      <section data-animate="fade-up-2" className="grid gap-4 md:grid-cols-3">
        <Card className="anim-delay-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UploadCloud className="tx-icon text-primary" />
              Start a Study
            </CardTitle>
            <CardDescription>Upload 3 or 4 BraTS-style NIfTI modality files and trigger the pipeline.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button asChild disabled={isGuest} className="w-full justify-between">
              <Link href="/upload">
                Upload MRI
                <ArrowRight className="tx-icon" />
              </Link>
            </Button>
            <p className="text-xs text-slate-500">Disabled in guest mode.</p>
          </CardContent>
        </Card>

        <Card className="anim-delay-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderKanban className="tx-icon text-primary" />
              Review Studies
            </CardTitle>
            <CardDescription>Track study status, QC, and available artifacts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button asChild className="w-full justify-between">
              <Link href="/studies">
                Open Studies
                <ArrowRight className="tx-icon" />
              </Link>
            </Button>
            <p className="text-xs text-slate-500">Includes report and export links.</p>
          </CardContent>
        </Card>

        <Card className="anim-delay-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers3 className="tx-icon text-primary" />
              Longitudinal Compare
            </CardTitle>
            <CardDescription>Compare two studies with RANO-style response labels.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button asChild disabled={isGuest} className="w-full justify-between">
              <Link href="/compare">
                Run Comparison
                <ArrowRight className="tx-icon" />
              </Link>
            </Button>
            <p className="text-xs text-slate-500">Disabled in guest mode.</p>
          </CardContent>
        </Card>
      </section>

      <section data-animate="fade-up-2" className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GaugeCircle className="tx-icon text-primary" />
              Recommended Study Flow
            </CardTitle>
            <CardDescription>Keep this sequence to reduce processing and review errors.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-700">
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">1. Upload MRI data and verify sequence metadata.</div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">2. Run synthesis plus segmentation to generate artifacts.</div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">3. Validate QC flags and volumetric metrics.</div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">4. Export report bundle (PDF, DICOM-SEG, JSON, STL).</div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">5. Compare current and prior studies for response trend.</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="tx-icon text-primary" />
              Viewer Shortcuts
            </CardTitle>
            <CardDescription>Use keyboard controls for faster and more consistent review.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-700">
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
              <span className="font-semibold text-slate-900">[ / ]</span> Move through slices
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
              <span className="font-semibold text-slate-900">U</span> Toggle uncertainty overlay
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
              Adjust opacity slider to inspect margins and edema
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
              Switch WT / TC / ET labels for focused QC
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
