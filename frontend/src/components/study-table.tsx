import Link from "next/link";
import { FileText, Play, Trash2, UploadCloud } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { EmptyState } from "./ui/empty-state";
import { SequenceChips } from "./sequence-chips";
import { formatDate } from "../lib/utils";
import type { Study } from "../lib/types";

interface StudyTableProps {
  studies: Study[];
  onRun: (id: string) => void;
  onDelete: (id: string) => void;
  isGuest?: boolean;
}

const STATUS_COLOR: Record<Study["status"], string> = {
  UPLOADED: "bg-slate-200 text-slate-700",
  PROCESSING: "bg-amber-100 text-amber-700",
  DONE: "bg-emerald-100 text-emerald-700",
  FAILED: "bg-rose-100 text-rose-600"
};

export function StudyTable({ studies, onRun, onDelete, isGuest = false }: StudyTableProps) {
  if (!studies.length) {
    return (
      <EmptyState
        icon={<UploadCloud className="tx-icon-lg" />}
        title="No studies yet"
        description="Upload 3 or 4 BraTS-style NIfTI modality files to create your first study."
        actions={
          <Button asChild>
            <Link href="/upload">Go to Upload</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Sequences</th>
            <th className="px-4 py-3">Created</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {studies.map((study) => (
            <tr key={study.id} className="text-sm">
              <td className="px-4 py-3 font-semibold text-slate-900">
                <Link href={`/study/${study.id}`} className="hover:underline">
                  {study.name}
                </Link>
              </td>
              <td className="px-4 py-3">
                <Badge className={STATUS_COLOR[study.status]}>{study.status}</Badge>
              </td>
              <td className="px-4 py-3">
                <SequenceChips sequences={study.sequences_present} />
              </td>
              <td className="px-4 py-3 text-slate-500">{formatDate(study.created_at)}</td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => onRun(study.id)} disabled={isGuest || study.status === "PROCESSING"}>
                    <Play className="tx-icon mr-1.5" />
                    Run Segmentation
                  </Button>
                  <Button variant="ghost" onClick={() => onDelete(study.id)} disabled={isGuest}>
                    <Trash2 className="tx-icon mr-1.5" />
                    Delete
                  </Button>
                  {isGuest ? (
                    <Button variant="ghost" disabled>
                      <FileText className="tx-icon mr-1.5" />
                      Report
                    </Button>
                  ) : study.status === "DONE" ? (
                    <Button asChild variant="ghost">
                      <Link href={`/report/${study.id}`}>
                        <FileText className="tx-icon mr-1.5" />
                        Report
                      </Link>
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
