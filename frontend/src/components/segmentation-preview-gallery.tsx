"use client";

import type { FileArtifact } from "../lib/types";
import { API_BASE } from "../lib/api";

interface SegmentationPreviewGalleryProps {
  studyId: string;
  files: FileArtifact[];
}

function labelForPreview(path: string) {
  const filename = path.split("/").pop() ?? path;
  return filename
    .replace(".png", "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function isSequencePreview(path: string) {
  return path.includes("_preview.png");
}

function isOverlayPreview(path: string) {
  return path.includes("_overlay.png");
}

function isConfidencePreview(path: string) {
  return path.includes("_confidence.png");
}

function groupLabel(path: string) {
  const filename = path.split("/").pop() ?? path;
  if (filename.startsWith("nnunet_")) return "nnU-Net";
  if (filename.startsWith("swinunetr_")) return "Swin UNETR";
  if (filename.startsWith("ensemble_")) return "Ensemble";
  return "Reference";
}

export function SegmentationPreviewGallery({ studyId, files }: SegmentationPreviewGalleryProps) {
  const previews = files
    .filter((file) => file.kind === "PNG")
    .sort((left, right) => left.path.localeCompare(right.path));

  if (!previews.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        Run segmentation to generate preview panels.
      </div>
    );
  }

  const apiBase = API_BASE;
  const sequencePreviews = previews.filter((file) => isSequencePreview(file.path));
  const overlayPreviews = previews.filter((file) => isOverlayPreview(file.path));
  const confidencePreviews = previews.filter((file) => isConfidencePreview(file.path));
  const anatomicalPreviews = previews.filter(
    (file) => !isSequencePreview(file.path) && !isOverlayPreview(file.path) && !isConfidencePreview(file.path)
  );
  const overlayGroups = Array.from(
    overlayPreviews.reduce((groups, file) => {
      const label = groupLabel(file.path);
      groups.set(label, [...(groups.get(label) ?? []), file]);
      return groups;
    }, new Map<string, FileArtifact[]>())
  );
  const confidenceGroups = Array.from(
    confidencePreviews.reduce((groups, file) => {
      const label = groupLabel(file.path);
      groups.set(label, [...(groups.get(label) ?? []), file]);
      return groups;
    }, new Map<string, FileArtifact[]>())
  );

  return (
    <div className="space-y-6">
      {sequencePreviews.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">All Sequences</h3>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {sequencePreviews.map((file) => (
              <figure key={file.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <img
                  src={`${apiBase}/studies/${studyId}/files/${file.id}/content`}
                  alt={labelForPreview(file.path)}
                  className="h-44 w-full object-cover"
                />
                <figcaption className="border-t border-slate-100 px-4 py-3 text-sm font-medium text-slate-700">
                  {labelForPreview(file.path)}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {overlayGroups.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Segmentation Overlays</h3>
          {overlayGroups.map(([groupName, groupFiles]) => (
            <div key={groupName} className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700">{groupName}</h4>
              <div className="grid gap-4 md:grid-cols-3">
                {groupFiles.map((file) => (
                  <figure key={file.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <img
                      src={`${apiBase}/studies/${studyId}/files/${file.id}/content`}
                      alt={labelForPreview(file.path)}
                      className="h-52 w-full object-cover"
                    />
                    <figcaption className="border-t border-slate-100 px-4 py-3 text-sm font-medium text-slate-700">
                      {labelForPreview(file.path)}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {confidenceGroups.length > 0 && (
        <section className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Confidence Maps</h3>
          {confidenceGroups.map(([groupName, groupFiles]) => (
            <div key={groupName} className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700">{groupName}</h4>
              <div className="grid gap-4 md:grid-cols-3">
                {groupFiles.map((file) => (
                  <figure key={file.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <img
                      src={`${apiBase}/studies/${studyId}/files/${file.id}/content`}
                      alt={labelForPreview(file.path)}
                      className="h-52 w-full object-cover"
                    />
                    <figcaption className="border-t border-slate-100 px-4 py-3 text-sm font-medium text-slate-700">
                      {labelForPreview(file.path)}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {anatomicalPreviews.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Reference Views</h3>
          <div className="grid gap-4 md:grid-cols-3">
            {anatomicalPreviews.map((file) => (
              <figure key={file.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <img
                  src={`${apiBase}/studies/${studyId}/files/${file.id}/content`}
                  alt={labelForPreview(file.path)}
                  className="h-52 w-full object-cover"
                />
                <figcaption className="border-t border-slate-100 px-4 py-3 text-sm font-medium text-slate-700">
                  {labelForPreview(file.path)}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
