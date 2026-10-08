"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import axios from "axios";
import { AlertTriangle, BarChart3, GitCompareArrows, Sparkles } from "lucide-react";
import { compareStudies, fetchStudies } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { BrandHeroArt } from "../../components/brand-hero-art";
import { EmptyState } from "../../components/ui/empty-state";
import { Skeleton } from "../../components/ui/skeleton";
import { toast } from "sonner";
import { useGuestMode } from "../../lib/auth";

export default function ComparePage() {
  const isGuest = useGuestMode();
  const { data: studies = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ["studies"],
    queryFn: fetchStudies
  });
  const [studyA, setStudyA] = useState<string | null>(null);
  const [studyB, setStudyB] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof compareStudies>> | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: () => {
      if (!studyA || !studyB) throw new Error("Select two studies to compare.");
      if (studyA === studyB) throw new Error("Select two different studies to compare.");
      return compareStudies(studyA, studyB);
    },
    onSuccess: (comparison) => {
      setResult(comparison);
      toast.success("Comparison ready", {
        description: `RANO label: ${comparison.rano_label}`
      });
    },
    onError: (error: unknown) => {
      const description =
        axios.isAxiosError(error)
          ? typeof error.response?.data?.detail === "string"
            ? error.response.data.detail
            : error.message
          : error instanceof Error
            ? error.message
            : "Unknown error";
      toast.error("Comparison failed", {
        description
      });
    }
  });
  const sameStudySelected = Boolean(studyA && studyB && studyA === studyB);

  return (
    <div className="space-y-6" data-animate="fade-up">
      <header className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-[0_20px_42px_-30px_rgba(15,76,92,0.4)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight text-primary" style={{ fontFamily: "var(--font-display)" }}>
              <GitCompareArrows className="tx-icon-lg" />
              Compare Studies
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Select two processed studies to compare final ensemble tumor burden across time points.
            </p>
          </div>
          <BrandHeroArt className="hidden h-16 w-24 sm:block" />
        </div>
      </header>

      {isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6">
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-44" />
          </div>
        </div>
      ) : isError ? (
        <EmptyState
          icon={<AlertTriangle className="tx-icon-lg" />}
          title="Unable to load study list"
          description={error instanceof Error ? error.message : "Unexpected error while fetching studies."}
          actions={<Button onClick={() => void refetch()}>Retry</Button>}
        />
      ) : !studies.length ? (
        <EmptyState
          icon={<Sparkles className="tx-icon-lg" />}
          title="No studies available for comparison"
          description="Upload and process at least two studies before running a longitudinal comparison."
          actions={
            <Button asChild>
              <Link href="/upload">Upload Study</Link>
            </Button>
          }
        />
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <Selector
            label="Study A"
            studies={studies}
            value={studyA ?? ""}
            onChange={(value) => setStudyA(value || null)}
          />
          <Selector
            label="Study B"
            studies={studies}
            value={studyB ?? ""}
            onChange={(value) => setStudyB(value || null)}
          />
        </div>
        <Button
          className="mt-4"
          disabled={isGuest || isPending || !studyA || !studyB || sameStudySelected}
          onClick={() => mutate()}
        >
          Run comparison
        </Button>
        {isGuest && <p className="mt-2 text-sm text-amber-700">Guest mode: comparisons are disabled.</p>}
        {sameStudySelected && (
          <p className="mt-2 text-sm text-rose-600">Select two different studies to run a comparison.</p>
        )}
      </div>
      )}

      {result && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm" data-animate="fade-up-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <BarChart3 className="tx-icon text-primary" />
            Outcome
          </h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <Metric label="Baseline WT volume" value={`${result.volume_a_ml.toFixed(1)} ml`} />
            <Metric label="Follow-up WT volume" value={`${result.volume_b_ml.toFixed(1)} ml`} />
            <Metric label="% change" value={`${result.pct_change.toFixed(1)} %`} />
            <Metric label="RANO label" value={result.rano_label} highlight />
          </div>
          <p className="mt-3 text-sm text-slate-600">
            Comparison uses the final stored segmentation output for each study and highlights longitudinal tumor change.
          </p>
        </div>
      )}
    </div>
  );
}

function Selector({
  label,
  studies,
  value,
  onChange
}: {
  label: string;
  studies: Array<{ id: string; name: string }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm transition focus:border-primary focus:outline-none"
      >
        <option value="">Select study</option>
        {studies.map((study) => (
          <option key={study.id} value={study.id}>
            {study.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function Metric({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      {highlight ? <Badge className="mt-1 inline-block">{value}</Badge> : <p className="text-base font-semibold text-slate-900">{value}</p>}
    </div>
  );
}
