"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, LoaderCircle, CircleAlert, MinusCircle } from "lucide-react";
import type { ProcessingProgress, ProcessingStep, StudyStatus } from "../lib/types";

function percentage(value: number) {
  return `${Math.max(0, Math.min(100, value)).toFixed(1).replace(/\.0$/, "")}%`;
}

function ProgressBar({ value, label, failed = false }: { value: number; label: string; failed?: boolean }) {
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}
      className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full transition-[width] duration-300 ${failed ? "bg-rose-500" : "bg-primary"}`}
        style={{ width: `${value}%` }} />
    </div>
  );
}

function Step({ step, small = false }: { step: ProcessingStep; small?: boolean }) {
  const failed = step.status === "FAILED";
  return (
    <div className={`rounded-xl border p-3 ${failed ? "border-rose-200 bg-rose-50" : "border-slate-100 bg-slate-50"}`}>
      <div className="mb-2 flex items-start justify-between gap-3 text-sm">
        <div className="flex items-center gap-2">
          {step.status === "DONE" ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            : step.status === "RUNNING" ? <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-primary" />
            : failed ? <CircleAlert className="h-4 w-4 shrink-0 text-rose-600" />
            : step.status === "SKIPPED" ? <MinusCircle className="h-4 w-4 shrink-0 text-slate-400" />
            : <span className="h-4 w-4 shrink-0 rounded-full border border-slate-300" />}
          <span className={small ? "text-slate-600" : "font-medium text-slate-900"}>{step.label}</span>
        </div>
        <span className="shrink-0 text-xs text-slate-600">
          {step.status === "SKIPPED" ? "Skipped" : `${step.status === "PENDING" ? "Waiting · " : ""}${percentage(step.percent)}`}
        </span>
      </div>
      <ProgressBar value={step.percent} label={step.label} failed={failed} />
      {!step.children.length && step.status !== "PENDING" && step.status !== "SKIPPED" && (
        <p className="mt-1 text-xs text-slate-500">{step.completed} / {step.total} {step.unit}</p>
      )}
      {step.detail && <p className="mt-2 break-words text-xs text-slate-600">{step.detail}</p>}
      {!!step.children.length && (
        <details open={step.status === "RUNNING" || failed} className="mt-3">
          <summary className="cursor-pointer text-xs font-medium text-slate-600">Subprocess progress ({step.children.length})</summary>
          <div className="mt-2 space-y-2">{step.children.map(child => <Step key={child.id} step={child} small />)}</div>
        </details>
      )}
    </div>
  );
}

export function StudyProcessingTimeline({ progress, status, awaitingStart = false, connectionError = false }: {
  progress?: ProcessingProgress | null;
  status: StudyStatus;
  awaitingStart?: boolean;
  connectionError?: boolean;
}) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (status !== "PROCESSING") return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [status]);
  const failed = status === "FAILED";
  const elapsed = progress ? Math.max(0, Math.floor(((progress.finished_at ? Date.parse(progress.finished_at) : now) - Date.parse(progress.started_at)) / 1000)) : 0;
  const current = progress?.stages.flatMap(stage => stage.children.length ? stage.children : [stage]).find(step => step.status === "RUNNING");
  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm" aria-label="Processing progress">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Processing Progress</h2>
          <p className="mt-1 text-sm text-slate-600">
            {awaitingStart ? "Waiting for the backend to start the requested run."
              : failed ? progress?.error ?? "Processing failed. You can retry the study."
              : status === "DONE" ? "Processing finished. Results are ready."
              : status === "PROCESSING" ? current?.label ?? "Processing is running on the server."
              : "Start segmentation to see measured progress."}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
          {progress ? percentage(progress.percent) : status === "DONE" ? "Complete" : "No measurement yet"}
        </span>
      </div>
      <p className="mb-2 mt-4 text-xs font-medium text-slate-600">Overall progress</p>
      <ProgressBar value={progress?.percent ?? (status === "DONE" ? 100 : 0)} label="Overall processing progress" failed={failed} />
      {progress ? (
        <>
          <div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
            <span>Elapsed: {Math.floor(elapsed / 60)}m {elapsed % 60}s</span>
            <span>Last measured update: {new Date(progress.updated_at).toLocaleTimeString()}</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">Progress comes from completed operations, slices, windows, and preprocessing iterations. Stages take different amounts of time; the percentage is not a time estimate.</p>
          {status === "PROCESSING" && <p className="mt-1 text-xs text-slate-500">A long operation may take time between updates. You can leave this page and return to the saved progress.</p>}
          <div className="mt-4 space-y-3">{progress.stages.map(stage => <Step key={stage.id} step={stage} />)}</div>
        </>
      ) : status !== "UPLOADED" && !awaitingStart ? (
        <p className="mt-3 text-sm text-slate-600">Per-step measurements are unavailable for this older run. New runs record progress on the server.</p>
      ) : null}
      {connectionError && <p role="alert" className="mt-3 text-sm text-amber-700">Cannot refresh progress right now. Showing the last saved measurement; reconnecting automatically.</p>}
    </section>
  );
}
