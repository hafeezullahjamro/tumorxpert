import type { Metrics } from "../lib/types";
import { Activity } from "lucide-react";
import { EmptyState } from "./ui/empty-state";
import { formatMl } from "../lib/utils";
import { useSettingsStore } from "../lib/store";

interface MetricsOverviewProps {
  metrics?: Metrics;
}

export function MetricsOverview({ metrics }: MetricsOverviewProps) {
  const units = useSettingsStore((state) => state.units);

  if (!metrics) {
    return (
      <EmptyState
        icon={<Activity className="tx-icon-lg" />}
        title="No metrics available yet"
        description="Run inference first. Quantitative metrics will appear here."
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">Final Ensemble Output</p>
      <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
        <MetricItem label="Whole Tumor" value={formatMl(metrics.wt_ml, units)} />
        <MetricItem label="Tumor Core" value={formatMl(metrics.tc_ml, units)} />
        <MetricItem label="Enhancing Tumor" value={formatMl(metrics.et_ml, units)} />
        <MetricItem label="Edema/Core Ratio" value={metrics.edema_core_ratio.toFixed(2)} />
        <MetricItem label="Confidence Summary" value={metrics.confidence_summary.toFixed(2)} />
        <MetricItem label="Low-Confidence Fraction" value={metrics.low_confidence_fraction.toFixed(2)} />
        {metrics.model_agreement_wt_dice != null && (
          <MetricItem label="Model Agreement (WT Dice)" value={metrics.model_agreement_wt_dice.toFixed(2)} />
        )}
        {metrics.label_disagreement_ml != null && (
          <MetricItem label="Label Disagreement" value={formatMl(metrics.label_disagreement_ml, units)} />
        )}
        <MetricItem label="Runtime" value={`${metrics.runtime_sec.toFixed(1)} s`} />
      </div>
    </div>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-base font-semibold text-slate-900">{value}</p>
    </div>
  );
}
