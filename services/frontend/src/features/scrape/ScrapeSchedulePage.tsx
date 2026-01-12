import React from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { ApiHttpError } from "@/api/http";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

function todayLocalIsoDate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function formatCodes(codes?: number[] | null): string {
  if (!codes || codes.length === 0) return "-";
  return codes.join(", ");
}

function formatKinds(kinds?: string[] | null): string {
  if (!kinds || kinds.length === 0) return "-";
  return kinds.join(", ");
}

export function ScrapeSchedulePage(): React.JSX.Element {
  const ctx = useApiCtx();
  const [raceDate, setRaceDate] = React.useState(todayLocalIsoDate());

  const qSchedule = useQuery({
    queryKey: ["scrape-schedule"],
    queryFn: () => api.scrapeScheduleStatus(ctx),
  });

  const qPlan = useQuery({
    queryKey: ["scrape-plan", raceDate],
    queryFn: () => api.scrapePlan(ctx, { race_date: raceDate }),
    retry: (count, error) => !(error instanceof ApiHttpError && error.status === 404) && count < 2,
  });

  const planNotFound = qPlan.error instanceof ApiHttpError && qPlan.error.status === 404;

  const planItems = React.useMemo(() => {
    const items = qPlan.data?.items ? [...qPlan.data.items] : [];
    items.sort((a, b) => {
      const ta = Date.parse(a.scheduled_at);
      const tb = Date.parse(b.scheduled_at);
      if (ta !== tb) return ta - tb;
      if (a.priority !== b.priority) return b.priority - a.priority;
      if (a.race_key.baba_code !== b.race_key.baba_code) return a.race_key.baba_code - b.race_key.baba_code;
      const ra = a.race_key.race_no ?? 0;
      const rb = b.race_key.race_no ?? 0;
      return ra - rb;
    });
    return items;
  }, [qPlan.data?.items]);

  return (
    <div>
      <h1 className="pageTitle">Scrape Schedule</h1>
      <p className="pageDesc">定期スクレイピングの実行予定（scrape plan）を表示します。</p>

      {qSchedule.isLoading ? <Loading label="Loading schedule..." /> : null}
      {qSchedule.error ? <ErrorBox error={qSchedule.error} /> : null}

      {qSchedule.data ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">Current Schedule</h2>
            <span className={qSchedule.data.enabled ? "pill ok" : "pill"}>{qSchedule.data.enabled ? "ENABLED" : "DISABLED"}</span>
            <button className="btn" onClick={() => qSchedule.refetch()}>
              Refresh
            </button>
          </div>
          <div className="small">baba_codes: {formatCodes(qSchedule.data.baba_codes)}</div>
          <div className="small">snapshot_kinds: {formatKinds(qSchedule.data.snapshot_kinds)}</div>
          <div className="small">prefetch_days: {qSchedule.data.prefetch_days ?? "-"}</div>
          <div className="small">updated_at: {qSchedule.data.updated_at}</div>
        </div>
      ) : null}

      <div className="card">
        <div className="cardHeader">
          <h2 className="cardTitle">Odds Plan</h2>
          <button className="btn" onClick={() => qPlan.refetch()}>
            Refresh
          </button>
        </div>

        <div className="row" style={{ marginBottom: 10 }}>
          <label>
            <div className="small">race_date (JST)</div>
            <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
          </label>
        </div>

        {qPlan.isLoading ? <Loading label="Loading scrape plan..." /> : null}
        {qPlan.error && !planNotFound ? <ErrorBox error={qPlan.error} /> : null}
        {planNotFound ? <div className="alert">scrape plan が見つかりません（scrape scheduled 実行後に生成されます）。</div> : null}

        {qPlan.data ? (
          <div className="small" style={{ marginBottom: 10 }}>
            generated_at: {qPlan.data.generated_at} / snapshot_kinds: {qPlan.data.snapshot_kinds.join(", ")} / interval_sec:{" "}
            {qPlan.data.interval_sec} / tolerance_sec: {qPlan.data.tolerance_sec} / items: {qPlan.data.items.length}
          </div>
        ) : null}

        {planItems.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>scheduled_at</th>
                <th>target_at</th>
                <th>task_kind</th>
                <th>baba_code</th>
                <th>race_no</th>
                <th>page_name</th>
                <th>snapshot_kind</th>
                <th>odds_flg</th>
                <th>priority</th>
                <th>delay_sec</th>
                <th>within_tolerance</th>
                <th>start_time</th>
              </tr>
            </thead>
            <tbody>
              {planItems.map((it, idx) => (
                <tr key={`${it.race_key.race_date}-${it.race_key.baba_code}-${it.race_key.race_no}-${it.snapshot_kind}-${idx}`}>
                  <td>{it.scheduled_at}</td>
                  <td>{it.target_at}</td>
                  <td>{it.task_kind}</td>
                  <td>{it.race_key.baba_code}</td>
                  <td>{it.race_key.race_no ?? "-"}</td>
                  <td>{it.page_name}</td>
                  <td>{it.snapshot_kind}</td>
                  <td>{it.odds_flg ?? "-"}</td>
                  <td>{it.priority}</td>
                  <td>{it.delay_sec}</td>
                  <td>{it.within_tolerance ? "ok" : "late"}</td>
                  <td>{it.start_time ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
