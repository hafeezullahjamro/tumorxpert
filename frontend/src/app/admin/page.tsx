"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchStorageOverview, updateRetention } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { formatBytes } from "../../lib/utils";
import { toast } from "sonner";

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["admin", "storage"],
    queryFn: fetchStorageOverview
  });

  const mutation = useMutation({
    mutationFn: updateRetention,
    onSuccess: () => {
      toast.success("Retention updated");
      queryClient.invalidateQueries({ queryKey: ["admin", "storage"] });
    },
    onError: (error: unknown) => {
      toast.error("Update failed", {
        description: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-primary">Admin</h1>
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Storage usage</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {data
            ? Object.entries(data.usage).map(([bucket, stats]) => (
                <div key={bucket} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{bucket}</p>
                  <p className="text-base font-semibold text-slate-900">{formatBytes(stats.bytes)}</p>
                  <p className="text-xs text-slate-500">{stats.files} files</p>
                </div>
              ))
            : "Loading..."}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Auto-delete policy</h2>
        {data && (
          <p className="text-sm text-slate-500">
            Currently {data.auto_delete_enabled ? "enabled" : "disabled"} - removing artifacts older than {data.auto_delete_days} days.
          </p>
        )}
        <form
          key={data ? `${data.auto_delete_days}-${data.auto_delete_enabled}` : "loading"}
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const days = Number(formData.get("days"));
            const enabled = formData.get("enabled") === "on";
            mutation.mutate({ days, enabled });
          }}
        >
          <label className="flex flex-col gap-2 text-sm text-slate-700">
            Retention days
            <input
              name="days"
              type="number"
              min={1}
              max={365}
              required
              defaultValue={data?.auto_delete_days ?? 7}
              className="w-32 rounded-md border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            Enable auto-delete
            <input name="enabled" type="checkbox" defaultChecked={data?.auto_delete_enabled} />
          </label>
          <Button type="submit" disabled={!data || mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </form>
      </section>
    </div>
  );
}
