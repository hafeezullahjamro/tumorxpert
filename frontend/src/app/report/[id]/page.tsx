"use client";

import { useQuery } from "@tanstack/react-query";
import { notFound, useParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, Download, FileSearch } from "lucide-react";
import { API_BASE, fetchStudy } from "../../../lib/api";
import { SequenceChips } from "../../../components/sequence-chips";
import { Button } from "../../../components/ui/button";
import { EmptyState } from "../../../components/ui/empty-state";
import { Skeleton } from "../../../components/ui/skeleton";
import { useGuestMode } from "../../../lib/auth";

export default function ReportPage() {
  const isGuest = useGuestMode();
  const params = useParams<{ id: string }>();
  const studyId = params?.id;
  if (!studyId) notFound();

  const {
    data: study,
    isLoading,
    isError,
    error,
    refetch
  } = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => fetchStudy(studyId)
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-[720px] w-full" />
      </div>
    );
  }

  if (isError || !study) {
    return (
      <EmptyState
        icon={<AlertTriangle className="tx-icon-lg" />}
        title="Unable to load report"
        description={error instanceof Error ? error.message : "Report data is currently unavailable."}
        actions={<Button onClick={() => void refetch()}>Retry</Button>}
      />
    );
  }

  if (study.status !== "DONE") {
    return (
      <EmptyState
        icon={<FileSearch className="tx-icon-lg" />}
        title="Report is not ready yet"
        description="Complete segmentation before viewing or downloading a report."
        actions={<Button asChild><Link href={`/study/${study.id}`}>Open study</Link></Button>}
      />
    );
  }

  const apiBase = API_BASE;
  const pdfUrl = `${apiBase}/studies/${studyId}/export/pdf`;
  const segUrl = `${apiBase}/studies/${studyId}/export/seg`;
  const jsonUrl = `${apiBase}/studies/${studyId}/export/json`;
  const stlUrl = `${apiBase}/studies/${studyId}/export/stl`;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight text-primary" style={{ fontFamily: "var(--font-display)" }}>
          <FileSearch className="tx-icon-lg" />
          Report - {study.name}
        </h1>
        <SequenceChips sequences={study.sequences_present} />
        {!isGuest ? (
          <div className="mt-4 flex flex-wrap gap-3">
            <Button asChild>
              <a href={pdfUrl} target="_blank" rel="noopener noreferrer">
                <Download className="tx-icon mr-1.5" />
                Download PDF
              </a>
            </Button>
            <Button asChild variant="secondary">
              <a href={segUrl} target="_blank" rel="noopener noreferrer">
                <Download className="tx-icon mr-1.5" />
                Download DICOM-SEG
              </a>
            </Button>
            <Button asChild variant="ghost">
              <a href={jsonUrl} target="_blank" rel="noopener noreferrer">
                <Download className="tx-icon mr-1.5" />
                Metrics JSON
              </a>
            </Button>
            <Button asChild variant="ghost">
              <a href={stlUrl} target="_blank" rel="noopener noreferrer">
                <Download className="tx-icon mr-1.5" />
                STL Mesh
              </a>
            </Button>
          </div>
        ) : (
          <div className="mt-4 space-y-2 text-sm text-amber-700">
            <p>Guest mode: downloads are disabled.</p>
            <Button asChild variant="secondary">
              <Link href="/auth/login">Sign in for exports</Link>
            </Button>
          </div>
        )}
      </div>

      {!isGuest && (
        <div className="h-[720px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow">
          <iframe title="PDF preview" src={pdfUrl} className="h-full w-full" />
        </div>
      )}
    </div>
  );
}
