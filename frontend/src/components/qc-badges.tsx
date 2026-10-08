interface QCBadgesProps {
  qcFlags: Record<string, string>;
}

export function QCBadges({ qcFlags }: QCBadgesProps) {
  const entries = Object.entries(qcFlags ?? {});
  if (entries.length === 0) {
    return <p className="text-sm text-emerald-600">QC clean - All heuristics passed.</p>;
  }
  return (
    <ul className="space-y-1 text-sm text-rose-600">
      {entries.map(([key, message]) => (
        <li key={key}>
          <span className="font-semibold uppercase tracking-wide">{key}:</span> {message}
        </li>
      ))}
    </ul>
  );
}
