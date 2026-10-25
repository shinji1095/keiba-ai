import React from "react";
import { statusLabel } from "@/shared/labels";

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
        <h2 className="cardTitle">データ同期</h2>
        <span className={statusClass}>{statusLabel(lastStatus)}</span>
      </div>

      {isLoading ? <Loading label="同期の状態を確認中…" /> : null}
      {loadError ? <ErrorBox error={loadError} /> : null}
      {saveError ? <ErrorBox error={saveError} /> : null}
      {triggerError ? <ErrorBox error={triggerError} /> : null}

      {status ? (
        <div className="small" style={{ marginBottom: 10 }}>
          最終同期日時： {formatDate(status.last_synced_at)}
          <br />
          最終実行日時： {formatDate(status.last_attempted_at)}
          <br />
          次回実行予定： {formatDate(status.next_scheduled_at)}
          <br />
          設定更新日時： {formatDate(status.schedule_updated_at)}
          {status.last_error ? (
            <>
              <br />
              直近のエラー： {status.last_error}
            </>
          ) : null}
        </div>
      ) : null}

      <div className="row">
        <label>
          <div className="small">自動実行を有効にする</div>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        </label>

        <label>
          <div className="small">同期間隔（日）</div>
          <input
            className="input"
            type="number"
            min={1}
            value={Number.isFinite(intervalDays) ? intervalDays : ""}
            onChange={(e) => setIntervalDays(Number(e.target.value))}
          />
        </label>

        <button className="btn" onClick={onRefresh}>
          更新
        </button>

        <button className="btn" onClick={handleSave} disabled={saving || !intervalValid}>
          {saving ? "保存中…" : "保存"}
        </button>

        <button className="btn primary" onClick={onTrigger} disabled={triggering}>
          {triggering ? "実行中…" : "今すぐ同期"}
        </button>
      </div>

      {!intervalValid ? <div className="small">同期間隔は1日以上で指定してください。</div> : null}
    </div>
  );
}
