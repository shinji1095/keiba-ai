import React from "react";

import { ScrapeSyncScheduleRequest, ScrapeSyncStatus } from "@/api/generated";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

type Props = {
  status?: ScrapeSyncStatus;
  isLoading: boolean;
  loadError?: unknown;
  saveError?: unknown;
  triggerError?: unknown;
  saving?: boolean;
  triggering?: boolean;
  onSave: (payload: ScrapeSyncScheduleRequest) => void;
  onTrigger: () => void;
  onRefresh: () => void;
};

function formatDate(value?: string | null): string {
  return value || "-";
}

export function SyncControlCard({
  status,
  isLoading,
  loadError,
  saveError,
  triggerError,
  saving,
  triggering,
  onSave,
  onTrigger,
  onRefresh,
}: Props): React.JSX.Element {
  const [enabled, setEnabled] = React.useState(false);
  const [intervalDays, setIntervalDays] = React.useState(2);

  React.useEffect(() => {
    if (status) {
      setEnabled(status.enabled);
      setIntervalDays(status.interval_days);
    }
  }, [status?.enabled, status?.interval_days]);

  const intervalValid = Number.isFinite(intervalDays) && intervalDays >= 1;
  const lastStatus = status?.last_status || "unknown";
  const statusClass =
    lastStatus === "success" ? "pill ok" : lastStatus === "failed" ? "pill bad" : "pill";

  const handleSave = () => {
    if (!intervalValid) return;
    const payload: ScrapeSyncScheduleRequest = {
      enabled,
      interval_days: Math.floor(intervalDays),
      diff_enabled: status?.diff_enabled ?? undefined,
    };
    onSave(payload);
  };

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="cardHeader">
        <h2 className="cardTitle">Sync Scheduler</h2>
        <span className={statusClass}>{lastStatus.toUpperCase()}</span>
      </div>

      {isLoading ? <Loading label="Loading sync status..." /> : null}
      {loadError ? <ErrorBox error={loadError} /> : null}
      {saveError ? <ErrorBox error={saveError} /> : null}
      {triggerError ? <ErrorBox error={triggerError} /> : null}

      {status ? (
        <div className="small" style={{ marginBottom: 10 }}>
          last_synced_at: {formatDate(status.last_synced_at)}
          <br />
          last_attempted_at: {formatDate(status.last_attempted_at)}
          <br />
          next_scheduled_at: {formatDate(status.next_scheduled_at)}
          <br />
          schedule_updated_at: {formatDate(status.schedule_updated_at)}
          {status.last_error ? (
            <>
              <br />
              last_error: {status.last_error}
            </>
          ) : null}
        </div>
      ) : null}

      <div className="row">
        <label>
          <div className="small">enabled</div>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        </label>

        <label>
          <div className="small">interval_days</div>
          <input
            className="input"
            type="number"
            min={1}
            value={Number.isFinite(intervalDays) ? intervalDays : ""}
            onChange={(e) => setIntervalDays(Number(e.target.value))}
          />
        </label>

        <button className="btn" onClick={onRefresh}>
          Refresh
        </button>

        <button className="btn" onClick={handleSave} disabled={saving || !intervalValid}>
          {saving ? "Saving..." : "Save"}
        </button>

        <button className="btn primary" onClick={onTrigger} disabled={triggering}>
          {triggering ? "Running..." : "Manual Sync"}
        </button>
      </div>

      {!intervalValid ? <div className="small">interval_days は 1 以上で指定してください。</div> : null}
    </div>
  );
}
