"use client";

import { CheckCircle2, LoaderCircle, CircleAlert } from "lucide-react";

interface StudyProcessingTimelineProps {
  steps: string[];
  activeStep: number;
  isRunning: boolean;
  hasError?: boolean;
  errorMessage?: string;
}

export function StudyProcessingTimeline({
  steps,
  activeStep,
  isRunning,
  hasError = false,
  errorMessage
}: StudyProcessingTimelineProps) {
  const completedSteps = isRunning ? activeStep : activeStep >= steps.length ? steps.length : activeStep;
  const progress = steps.length ? Math.min(100, Math.round((completedSteps / steps.length) * 100)) : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Processing Progress</h2>
          <p className="mt-1 text-sm text-slate-600">
            {hasError
              ? errorMessage ?? "The run failed before completion."
              : isRunning
              ? "Segmentation is running. Steps will complete as the pipeline advances."
              : progress === 100
              ? "Segmentation finished. Results and previews are ready below."
              : "Start segmentation to see the pipeline timeline."}
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">{progress}%</span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-700 ${hasError ? "bg-rose-500" : "bg-primary"}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-4 space-y-3">
        {steps.map((step, index) => {
          const isComplete = completedSteps > index;
          const isCurrent = isRunning && completedSteps === index;
          const isFailed = hasError && completedSteps === index;
          return (
            <div key={step} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
              {isComplete ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : isCurrent ? (
                <LoaderCircle className="h-4 w-4 animate-spin text-primary" />
              ) : isFailed ? (
                <CircleAlert className="h-4 w-4 text-rose-600" />
              ) : (
                <div className="h-4 w-4 rounded-full border border-slate-300" />
              )}
              <span className={`${isComplete ? "text-slate-900" : "text-slate-600"}`}>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
