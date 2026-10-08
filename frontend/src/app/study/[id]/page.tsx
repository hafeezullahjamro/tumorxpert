"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notFound, useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, FileArchive, FileText, Microscope, Play, ScanEye } from "lucide-react";
import { MetricsOverview } from "../../../components/metrics-overview";
import { SegmentationPreviewGallery } from "../../../components/segmentation-preview-gallery";
import { SequenceChips } from "../../../components/sequence-chips";
import { StudyProcessingTimeline } from "../../../components/study-processing-timeline";
import { QCBadges } from "../../../components/qc-badges";
import { FileList } from "../../../components/file-list";
import { EmptyState } from "../../../components/ui/empty-state";
import { Button } from "../../../components/ui/button";
import { Skeleton } from "../../../components/ui/skeleton";
import axios from "axios";
import { fetchFiles, fetchMetrics, fetchStudy, getApiErrorMessage, runStudy } from "../../../lib/api";
import { useGuestMode } from "../../../lib/auth";
import { toast } from "sonner";

export default function StudyDetailPage() {
  const isGuest = useGuestMode();
  const queryClient = useQueryClient();
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const studyId = params?.id;
  if (!studyId) notFound();
  const [activeStep, setActiveStep] = useState(0);
  const [autoStarted, setAutoStarted] = useState(false);

  const {
    data: study,
    isLoading: studyLoading,
    isError: studyError,
    error: studyErrorValue,
    refetch: refetchStudy
  } = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => fetchStudy(studyId),
    refetchInterval: (query) => query.state.data?.status === "PROCESSING" ? 5000 : false
  });
  const { data: metrics } = useQuery({
    queryKey: ["study", studyId, "metrics"],
    queryFn: async () => {
      try {
        return await fetchMetrics(studyId);
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
    enabled: study?.status === "DONE"
  });
  const { data: files = [] } = useQuery({
    queryKey: ["study", studyId, "files"],
    queryFn: async () => {
      try {
        return await fetchFiles(studyId);
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          return [];
        }
        throw error;
      }
    }
  });
  const runSteps = useMemo(() => {
    const steps = ["Validate uploaded modalities", "Preprocess study volumes"];
    const missingModalities = Object.values(study?.sequences_present ?? {}).filter((present) => !present).length;
    if (missingModalities === 1) {
      steps.push("Synthesize the missing modality");
    }
    steps.push("Run nnU-Net segmentation");
    steps.push("Run Swin UNETR segmentation");
    steps.push("Fuse model probabilities into ensemble output");
    steps.push("Generate metrics and exports");
    steps.push("Render preview images");
    return steps;
  }, [study?.sequences_present]);
  const hasPdfReport = files.some((file) => file.kind === "PDF");

  const runMutation = useMutation({
    mutationFn: runStudy,
    onSuccess: async () => {
      setActiveStep(runSteps.length);
      toast.success("Segmentation finished", {
        description: "Per-model outputs, the final ensemble result, and exports are ready."
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["studies"] }),
        queryClient.invalidateQueries({ queryKey: ["study", studyId] }),
        queryClient.invalidateQueries({ queryKey: ["study", studyId, "metrics"] }),
        queryClient.invalidateQueries({ queryKey: ["study", studyId, "files"] })
      ]);
    },
    onError: (error: unknown) => {
      toast.error("Run failed", {
        description: getApiErrorMessage(error)
      });
    }
  });

  useEffect(() => {
    if (!runMutation.isPending) return;
    const interval = window.setInterval(() => {
      setActiveStep((current) => Math.min(current + 1, Math.max(runSteps.length - 1, 0)));
    }, 1800);
    return () => window.clearInterval(interval);
  }, [runMutation.isPending, runSteps.length]);

  useEffect(() => {
    const shouldAutoRun = searchParams.get("run") === "1";
    if (isGuest || !shouldAutoRun || !study || autoStarted || runMutation.isPending || study.status === "PROCESSING") return;
    setAutoStarted(true);
    setActiveStep(0);
    runMutation.mutate(study.id);
  }, [autoStarted, isGuest, runMutation, searchParams, study]);

  if (studyLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-[520px] w-full" />
        </div>
        <aside className="space-y-6">
          <Skeleton className="h-52 w-full" />
          <Skeleton className="h-64 w-full" />
        </aside>
      </div>
    );
  }

  if (studyError || !study) {
    return (
      <EmptyState
        icon={<AlertTriangle className="tx-icon-lg" />}
        title="Unable to load this study"
        description={studyErrorValue instanceof Error ? studyErrorValue.message : "This study may have been removed or is temporarily unavailable."}
        actions={<Button onClick={() => void refetchStudy()}>Retry</Button>}
      />
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
      <div className="flex flex-col gap-6">
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-primary">{study.name}</h1>
              <p className="text-sm text-slate-500">Status: {study.status}</p>
            </div>
            <div className="flex flex-col items-end gap-3">
              <SequenceChips sequences={study.sequences_present} />
              <div className="flex items-center gap-2">
                {!isGuest && (
                  <Button
                    onClick={() => {
                      setActiveStep(0);
                      runMutation.mutate(study.id);
                    }}
                    disabled={runMutation.isPending || study.status === "PROCESSING"}
                  >
                    <Play className="tx-icon mr-1.5" />
                    {study.status === "DONE" ? "Re-run Segmentation" : "Run Segmentation"}
                  </Button>
                )}
                {!isGuest && study.status === "DONE" && hasPdfReport && (
                  <Button asChild variant="secondary">
                    <Link href={`/report/${study.id}`}>
                      <FileText className="tx-icon mr-1.5" />
                      View Report
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          </div>
          <div className="mt-4">
            <QCBadges qcFlags={study.qc_flags} />
          </div>
          <p className="mt-3 text-sm text-slate-500">
            Full MRI scans can take several minutes to process on a CPU.
          </p>
        </div>
        <StudyProcessingTimeline
          steps={runSteps}
          activeStep={runMutation.isPending ? activeStep : study.status === "DONE" ? runSteps.length : activeStep}
          isRunning={runMutation.isPending}
          hasError={runMutation.isError}
          errorMessage={runMutation.isError ? getApiErrorMessage(runMutation.error) : undefined}
        />
        <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <ScanEye className="tx-icon text-primary" />
            Scan, Model, And Ensemble Previews
          </h2>
          <SegmentationPreviewGallery studyId={study.id} files={files} />
        </section>
      </div>
      <aside className="space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <Microscope className="tx-icon text-primary" />
            Segmentation Metrics
          </h2>
          <MetricsOverview metrics={metrics ?? undefined} />
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <FileArchive className="tx-icon text-primary" />
            Artifacts
          </h2>
          {isGuest ? (
            <p className="text-sm text-amber-700">Guest mode: downloads are disabled.</p>
          ) : (
            <FileList studyId={study.id} files={files} />
          )}
        </section>
      </aside>
    </div>
  );
}
