"use client";

import { useState } from "react";
import { FileUp, FolderOpen } from "lucide-react";
import { Button } from "./ui/button";

interface UploadDropzoneProps {
  onUpload: (files: File[]) => Promise<void>;
}

export function UploadDropzone({ onUpload }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [fileSummary, setFileSummary] = useState<string | null>(null);
  const [uploadSucceeded, setUploadSucceeded] = useState(false);

  const handleFiles = async (files: File[]) => {
    if (!files.length || isUploading) return;
    setFileSummary(files.length === 1 ? files[0].name : `${files.length} modality files selected`);
    setUploadSucceeded(false);
    setIsUploading(true);
    try {
      await onUpload(files);
      setUploadSucceeded(true);
    } catch {
      // The upload page shows the server error. Keep this label accurate after a failed request.
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        const files = Array.from(event.dataTransfer.files ?? []);
        if (files.length) void handleFiles(files);
      }}
      className={`flex h-60 flex-col items-center justify-center rounded-2xl border-2 border-dashed ${
        isDragging ? "border-primary bg-white shadow-[0_14px_32px_-24px_rgba(15,76,92,0.6)]" : "border-slate-300 bg-white/80"
      } p-6 text-center transition`}
    >
      <div className="mb-2 rounded-xl bg-accent/70 p-2 text-primary">
        <FileUp className="tx-icon-lg" />
      </div>
      <p className="text-lg font-semibold text-slate-800">Drop DICOM ZIP, BraTS NIfTI files, or one TAR archive</p>
      <p className="mt-2 text-sm text-slate-500">
        Supported uploads: `.zip` (DICOM or zipped BraTS NIfTI), `.tar`, `.tar.gz`, `.tgz`, `.nii`, `.nii.gz`.
        Supported names: `*_0000.nii.gz` to `*_0003.nii.gz` or `*_flair.nii.gz`, `*_t1.nii.gz`, `*_t1ce.nii.gz`, `*_t2.nii.gz`.
      </p>
      <Button variant="secondary" asChild className="mt-4">
        <label className="cursor-pointer">
          <FolderOpen className="tx-icon mr-1.5 inline" />
          Browse files
          <input
            type="file"
            className="hidden"
            accept=".nii,.nii.gz,.tar,.tar.gz,.tgz,.zip"
            multiple
            disabled={isUploading}
            onChange={(event) => {
              const files = Array.from(event.target.files ?? []);
              event.target.value = "";
              if (files.length) void handleFiles(files);
            }}
          />
        </label>
      </Button>
      {fileSummary && (
        <p className="mt-3 text-sm text-primary">
          {isUploading ? "Uploading..." : uploadSucceeded ? `Uploaded ${fileSummary}` : `Upload failed: ${fileSummary}`}
        </p>
      )}
    </div>
  );
}
