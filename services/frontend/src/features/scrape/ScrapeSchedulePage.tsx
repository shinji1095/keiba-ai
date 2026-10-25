import React from "react";
import { scrapeTargetLabel, snapshotKindLabel } from "@/shared/labels";
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
  return kinds.map(snapshotKindLabel).join("、");
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
      <h1 className="pageTitle">収集スケジュール</h1>
      <p className="pageDesc">自動収集の設定と、オッズを取得する予定を確認できます。</p>

      {qSchedule.isLoading ? <Loading label="収集設定を読み込み中…" /> : null}
      {qSchedule.error ? <ErrorBox error={qSchedule.error} /> : null}

      {qSchedule.data ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">現在の収集設定</h2>
            <span className={qSchedule.data.enabled ? "pill ok" : "pill"}>{qSchedule.data.enabled ? "有効" : "無効"}</span>
            <button className="btn" onClick={() => qSchedule.refetch()}>
              更新
            </button>
          </div>
          <div className="small">対象の競馬場コード： {formatCodes(qSchedule.data.baba_codes)}</div>
          <div className="small">オッズの取得タイミング： {formatKinds(qSchedule.data.snapshot_kinds)}</div>
          <div className="small">先読み日数： {qSchedule.data.prefetch_days ?? "-"}</div>
          <div className="small">設定更新日時： {qSchedule.data.updated_at}</div>
        </div>
      ) : null}

      <div className="card">
        <div className="cardHeader">
          <h2 className="cardTitle">オッズの収集予定</h2>
          <button className="btn" onClick={() => qPlan.refetch()}>
            更新
          </button>
        </div>

        <div className="row" style={{ marginBottom: 10 }}>
          <label>
            <div className="small">開催日（日本時間）</div>
            <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
          </label>
        </div>

        {qPlan.isLoading ? <Loading label="収集予定を読み込み中…" /> : null}
        {qPlan.error && !planNotFound ? <ErrorBox error={qPlan.error} /> : null}
        {planNotFound ? <div className="alert">収集予定がありません。自動収集の処理が実行されると作成されます。</div> : null}

        {qPlan.data ? (
          <div className="small" style={{ marginBottom: 10 }}>
            予定作成日時： {qPlan.data.generated_at} / オッズの取得タイミング： {qPlan.data.snapshot_kinds.map(snapshotKindLabel).join("、")} / 取得間隔（秒）：{" "}
            {qPlan.data.interval_sec} / 許容遅延（秒）： {qPlan.data.tolerance_sec} / 件数： {qPlan.data.items.length}
          </div>
        ) : null}

        {planItems.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>実行予定日時</th>
                <th>目標取得日時</th>
                <th>処理の種類</th>
                <th>競馬場コード</th>
                <th>レース番号</th>
                <th>取得するページ</th>
                <th>取得タイミング</th>
                <th>オッズ区分</th>
                <th>優先度</th>
                <th>遅延（秒）</th>
                <th>許容範囲</th>
                <th>発走時刻</th>
              </tr>
            </thead>
            <tbody>
              {planItems.map((it, idx) => (
                <tr key={`${it.race_key.race_date}-${it.race_key.baba_code}-${it.race_key.race_no}-${snapshotKindLabel(it.snapshot_kind)}-${idx}`}>
                  <td>{it.scheduled_at}</td>
                  <td>{it.target_at}</td>
                  <td>{scrapeTargetLabel(it.task_kind)}</td>
                  <td>{it.race_key.baba_code}</td>
                  <td>{it.race_key.race_no ?? "-"}</td>
                  <td>{scrapeTargetLabel(it.page_name)}</td>
                  <td>{snapshotKindLabel(it.snapshot_kind)}</td>
                  <td>{it.odds_flg ?? "-"}</td>
                  <td>{it.priority}</td>
                  <td>{it.delay_sec}</td>
                  <td>{it.within_tolerance ? "範囲内" : "遅延"}</td>
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
