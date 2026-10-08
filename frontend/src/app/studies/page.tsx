"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { AlertTriangle, ClipboardList, UploadCloud } from "lucide-react";
import { deleteStudy, fetchStudies } from "../../lib/api";
import { StudyTable } from "../../components/study-table";
import { EmptyState } from "../../components/ui/empty-state";
import { Skeleton } from "../../components/ui/skeleton";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";
import { useGuestMode } from "../../lib/auth";

export default function StudiesPage() {
  const isGuest = useGuestMode();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: studies = [], isLoading, isError, error } = useQuery({
    queryKey: ["studies"],
    queryFn: fetchStudies
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStudy,
    onSuccess: () => {
      toast.success("Study deleted");
      queryClient.invalidateQueries({ queryKey: ["studies"] });
    },
    onError: (error: unknown) => {
      toast.error("Delete failed", {
        description: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight text-primary" style={{ fontFamily: "var(--font-display)" }}>
          <ClipboardList className="tx-icon-lg" />
          Studies
        </h1>
        <Button asChild disabled={isGuest}>
          <Link href="/upload">
            <UploadCloud className="tx-icon mr-1.5" />
            Upload New Study
          </Link>
        </Button>
      </header>
      {isGuest && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
          Guest mode: running inference, deleting studies, and reports are disabled.
        </div>
      )}
      {isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5">
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      ) : isError ? (
        <EmptyState
          icon={<AlertTriangle className="tx-icon-lg" />}
          title="Unable to load studies"
          description={error instanceof Error ? error.message : "Something went wrong while loading studies."}
          actions={
            <Button onClick={() => queryClient.invalidateQueries({ queryKey: ["studies"] })}>
              Retry
            </Button>
          }
        />
      ) : (
        <StudyTable
          studies={studies}
          isGuest={isGuest}
          onRun={(id) => router.push(`/study/${id}?run=1`)}
          onDelete={(id) => deleteMutation.mutate(id)}
        />
      )}
    </div>
  );
}
