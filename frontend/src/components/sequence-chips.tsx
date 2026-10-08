import { clsx } from "clsx";

interface SequenceChipsProps {
  sequences: Record<string, boolean>;
}

const LABELS: Record<string, string> = {
  t1: "T1",
  t1ce: "T1ce",
  t2: "T2",
  flair: "FLAIR"
};

export function SequenceChips({ sequences }: SequenceChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(LABELS).map(([key, label]) => {
        const available = Boolean(sequences?.[key]);
        return (
          <span
            key={key}
            title={available ? `${label} present` : `${label} missing`}
            className={clsx(
              "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide",
              available ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-600"
            )}
          >
            {label} {available ? "YES" : "NO"}
          </span>
        );
      })}
    </div>
  );
}
