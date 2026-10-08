import { formatBytes } from "../lib/utils";
import { API_BASE } from "../lib/api";
import type { FileArtifact } from "../lib/types";
import { ArchiveX } from "lucide-react";
import { Button } from "./ui/button";
import { EmptyState } from "./ui/empty-state";

interface FileListProps {
  studyId: string;
  files: FileArtifact[];
}

const LABELS: Record<FileArtifact["kind"], string> = {
  T1: "T1",
  T1CE: "T1ce",
  T2: "T2",
  FLAIR: "FLAIR",
  NIFTI: "Uploaded NIfTI",
  DICOM_ZIP: "DICOM Zip",
  SEG_NIFTI: "Segmentation (NIfTI)",
  SEG_DICOM: "Segmentation (DICOM-SEG)",
  PDF: "PDF Report",
  JSON: "Metrics JSON",
  STL: "Tumor Mesh (STL)",
  PNG: "Thumbnail"
};

const EXPORT_ENDPOINTS: Partial<Record<FileArtifact["kind"], string>> = {
  SEG_DICOM: "seg",
  PDF: "pdf",
  JSON: "json",
  STL: "stl"
};

export function FileList({ studyId, files }: FileListProps) {
  if (!files?.length) {
    return (
      <EmptyState
        icon={<ArchiveX className="tx-icon-lg" />}
        title="No artifacts yet"
        description="Run inference to generate segmentation, reports, and exportable files."
      />
    );
  }
  return (
    <div className="space-y-2">
      {files.map((file) => {
        const exportPath = EXPORT_ENDPOINTS[file.kind];
        const downloadHref = exportPath
          ? `${API_BASE}/studies/${studyId}/export/${exportPath}`
          : `${API_BASE}/studies/${studyId}/files/${file.id}/content`;
        const filename = file.path.split("/").pop() ?? file.path;
        const displayLabel =
          file.kind === "NIFTI" || file.kind === "PNG"
            ? filename.replaceAll("_", " ")
            : LABELS[file.kind];
        return (
          <div
            key={file.id}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <div>
              <p className="font-medium text-slate-800">{displayLabel}</p>
              <p className="text-xs text-slate-500">{formatBytes(file.size_bytes)}</p>
            </div>
            {downloadHref ? (
              <Button asChild variant="secondary">
                <a href={downloadHref} target="_blank" rel="noopener noreferrer">
                  Download
                </a>
              </Button>
            ) : (
              <span className="text-xs text-slate-400">Stored locally</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
