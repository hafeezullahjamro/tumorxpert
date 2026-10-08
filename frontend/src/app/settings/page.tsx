"use client";

import { useSettingsStore } from "../../lib/store";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";

export default function SettingsPage() {
  const { theme, changeThreshold, confidenceThreshold, units, setTheme, setChangeThreshold, setConfidenceThreshold, setUnits } =
    useSettingsStore();

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-primary">Settings</h1>
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <form className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm text-slate-700">
            Theme
            <select
              aria-label="Theme"
              value={theme}
              onChange={(event) => setTheme(event.currentTarget.value as typeof theme)}
              className="rounded-md border border-slate-200 px-3 py-2"
            >
              <option value="light">Light</option>
              <option value="dark" disabled>
                Dark (coming soon)
              </option>
            </select>
          </label>
          <label className="flex flex-col gap-2 text-sm text-slate-700">
            Stable-change threshold (%)
            <input
              type="number"
              value={changeThreshold}
              onChange={(event) => setChangeThreshold(Number(event.currentTarget.value))}
              className="rounded-md border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm text-slate-700">
            Confidence threshold
            <input
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={confidenceThreshold}
              onChange={(event) => setConfidenceThreshold(Number(event.currentTarget.value))}
              className="rounded-md border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm text-slate-700">
            Units
            <select
              aria-label="Units"
              value={units}
              onChange={(event) => setUnits(event.currentTarget.value as typeof units)}
              className="rounded-md border border-slate-200 px-3 py-2"
            >
              <option value="ml">Milliliters (ml)</option>
              <option value="cc">Cubic centimeters (cc)</option>
            </select>
          </label>
        </form>
        <Button className="mt-4" type="button" onClick={() => toast.success("Preferences saved on this browser.")}>
          Save preferences
        </Button>
      </section>
    </div>
  );
}
