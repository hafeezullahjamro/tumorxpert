"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import axios from "axios";
import { ArrowRight, CloudUpload, FileCheck2, FlaskConical, Lock } from "lucide-react";
import { uploadStudy } from "../../lib/api";
import { BrandHeroArt } from "../../components/brand-hero-art";
import { UploadDropzone } from "../../components/upload-dropzone";
import { SequenceChips } from "../../components/sequence-chips";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { EmptyState } from "../../components/ui/empty-state";
import { toast } from "sonner";
import { useGuestMode } from "../../lib/auth";

export default function UploadPage() {
  const isGuest = useGuestMode();

  const queryClient = useQueryClient();
  const [lastSequences, setLastSequences] = useState<Record<string, boolean> | null>(null);
  const [qcFlags, setQcFlags] = useState<Record<string, string>>({});
  const { mutateAsync, isPending } = useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const study = await uploadStudy(formData);
      setLastSequences(study.sequences_present);
      setQcFlags(study.qc_flags ?? {});
      await queryClient.invalidateQueries({ queryKey: ["studies"] });
      return study;
    },
    onSuccess: (study) => {
      toast.success(`Uploaded ${study.name}`, {
        description: "Run segmentation from the Studies view."
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
      toast.error("Upload failed", {
        description
      });
    }
  });

  return (
    <div className="space-y-8" data-animate="fade-up">
      <div className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-[0_20px_44px_-30px_rgba(15,76,92,0.4)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight text-primary" style={{ fontFamily: "var(--font-display)" }}>
              <CloudUpload className="tx-icon-lg" />
              Upload MRI Study
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Upload DICOM ZIP, zipped BraTS NIfTI, 3 or 4 aligned BraTS-style NIfTI modality files, or a single TAR archive containing
              them. Plain `.gz` files are only valid when they are actual `.nii.gz` files or part of a `.tar.gz` archive. The backend
              preprocesses the study, synthesises one missing modality when needed, runs nnU-Net and Swin UNETR, then generates a final
              ensemble result.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="rounded-full">Guest mode supported</Badge>
            <BrandHeroArt className="hidden h-16 w-24 sm:block" />
          </div>
        </div>
      </div>
      {isGuest ? (
        <EmptyState
          icon={<Lock className="tx-icon-lg" />}
          title="Uploads are locked in guest mode"
          description="Sign in to upload files, run inference, and keep studies in history."
          actions={
            <Button asChild>
              <Link href="/auth/login">Go to Login</Link>
            </Button>
          }
        />
      ) : (
        <>
          <UploadDropzone
            onUpload={async (files) => {
              if (isPending) return;
              await mutateAsync(files);
            }}
          />
          {isPending && <p className="text-sm text-slate-500">Uploading...</p>}
        </>
      )}
      {lastSequences && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm" data-animate="fade-up-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
            <FileCheck2 className="tx-icon text-primary" />
            Detected sequences
          </h2>
          <SequenceChips sequences={lastSequences} />
          <div className="mt-4 space-y-2 text-sm">
            <p className="inline-flex items-center gap-2 font-semibold text-slate-700">
              <FlaskConical className="tx-icon text-primary" />
              QC Heuristics
            </p>
            {Object.keys(qcFlags).length ? (
              <ul className="list-disc pl-5 text-rose-600">
                {Object.entries(qcFlags).map(([key, message]) => (
                  <li key={key}>
                    <span className="font-semibold uppercase tracking-wide">{key}</span>: {message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-emerald-600">All primary sequences present. Ready for inference.</p>
            )}
          </div>
          <div className="mt-4 flex gap-3">
            <Button asChild>
              <a href="/studies">
                View studies
                <ArrowRight className="tx-icon ml-1.5" />
              </a>
            </Button>
            <Button variant="ghost" asChild>
              <a href="/help">Review workflow</a>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
