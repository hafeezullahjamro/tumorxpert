"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notFound, useParams, useSearchParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
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
  const router = useRouter();
  const studyId = params?.id;
  if (!studyId) notFound();
  const [requestedRun, setRequestedRun] = useState(false);
  const autoStarted = useRef(false);

  const {
    data: study,
    isLoading: studyLoading,
    error: studyErrorValue,
    isRefetchError: progressConnectionError,
    refetch: refetchStudy
  } = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => fetchStudy(studyId),
    refetchInterval: (query) => query.state.data?.status === "PROCESSING" || requestedRun ? 1000 : false,
    refetchIntervalInBackground: true,
    refetchOnMount: "always",
    refetchOnWindowFocus: "always"
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
  const hasPdfReport = files.some((file) => file.kind === "PDF");

  const runMutation = useMutation({
    mutationFn: runStudy,
    onMutate: () => {
      setRequestedRun(true);
      void queryClient.invalidateQueries({ queryKey: ["study", studyId] });
    },
    onSuccess: async () => {
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
      toast.error("Processing request could not finish", {
        description: getApiErrorMessage(error)
      });
    },
    onSettled: () => {
      setRequestedRun(false);
      void queryClient.invalidateQueries({ queryKey: ["study", studyId] });
    }
  });

  useEffect(() => {
    if (isGuest || searchParams.get("run") !== "1" || !study || autoStarted.current) return;
    autoStarted.current = true;
    // Consume this action so history navigation cannot start another run.
    router.replace(`/study/${study.id}`, { scroll: false });
    if (study.status !== "PROCESSING") runMutation.mutate(study.id);
  }, [isGuest, router, runMutation, searchParams, study]);

  useEffect(() => {
    if (study?.status !== "DONE") return;
    void queryClient.invalidateQueries({ queryKey: ["study", studyId, "files"] });
    void queryClient.invalidateQueries({ queryKey: ["study", studyId, "metrics"] });
  }, [queryClient, studyId, study?.status]);

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

  if (!study) {
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
          progress={study.progress}
          status={study.status}
          awaitingStart={requestedRun && study.status !== "PROCESSING"}
          connectionError={progressConnectionError}
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
          <MetricsOverview metrics={study.status === "DONE" ? metrics ?? undefined : undefined} />
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
