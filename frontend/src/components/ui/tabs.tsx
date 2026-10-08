import { clsx } from "clsx";
import type { ReactNode } from "react";

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  activeId: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, activeId, onChange }: TabsProps) {
  return (
    <div className="flex gap-2 rounded-md bg-white/40 p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            "flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition",
            activeId === tab.id ? "bg-primary text-white shadow" : "text-slate-600 hover:bg-white"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
