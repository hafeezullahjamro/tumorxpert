"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Activity } from "lucide-react";
import { fetchStudies } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { EmptyState } from "../../components/ui/empty-state";
import { Skeleton } from "../../components/ui/skeleton";
import { formatDate } from "../../lib/utils";

export default function JobsPage() {
  const { data: studies = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ["studies"],
    queryFn: fetchStudies,
    refetchInterval: 5000
  });

  return (
    <div className="space-y-6">
      <h1 className="flex items-center gap-2 text-3xl font-bold text-primary">
        <Activity className="tx-icon-lg" />
        Processing Jobs
      </h1>
      <p className="text-sm text-slate-500">
        Live study status from the backend. Open a study to run or retry segmentation and review its results.
      </p>
      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : isError ? (
        <EmptyState
          icon={<AlertTriangle className="tx-icon-lg" />}
          title="Unable to load processing jobs"
          description={error instanceof Error ? error.message : "Study status is unavailable."}
          actions={<Button onClick={() => void refetch()}>Retry</Button>}
        />
      ) : !studies.length ? (
        <EmptyState
          title="No processing jobs yet"
          description="Upload a study and run segmentation to see its status here."
          actions={<Button asChild><Link href="/upload">Upload Study</Link></Button>}
        />
      ) : (
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
            <tr>
              <th className="px-4 py-3">Study</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {studies.map((study) => (
                <tr key={study.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{study.name}</td>
                  <td className="px-4 py-3 text-slate-600">{study.status}</td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(study.created_at)}</td>
                  <td className="px-4 py-3">
                    <Button asChild variant="secondary">
                      <Link href={`/study/${study.id}`}>{study.status === "FAILED" ? "Review and retry" : "Open study"}</Link>
                    </Button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}
