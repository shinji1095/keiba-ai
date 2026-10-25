import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { mergeVenues } from "@/shared/venues";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function TodayRacesPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const [babaCode, setBabaCode] = React.useState<string>("");
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(200);
  const raceDate = todayIsoDate();

  const qVenues = useQuery({
    queryKey: ["venues"],
    queryFn: () => api.listVenues(ctx),
  });
  const venues = mergeVenues(qVenues.data?.items);

  const qEntries = useQuery({
    queryKey: ["race-entries", raceDate, babaCode, page, pageSize],
    queryFn: () =>
      api.listRaceEntriesByDate(ctx, {
        race_date: raceDate,
        baba_code: babaCode ? Number(babaCode) : undefined,
        page,
        page_size: pageSize,
      }),
  });

  const canPrev = page > 1;
  const canNext = (qEntries.data?.items.length ?? 0) === pageSize;

  return (
    <div>
      <h1 className="pageTitle">本日の出走表</h1>
      <p className="pageDesc">
        本日（{raceDate}）の出走馬・騎手・斤量・馬体重を確認できます。
      </p>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <label>
            <div className="small">開催日</div>
            <input className="input" type="date" value={raceDate} disabled />
          </label>

          <label>
            <div className="small">競馬場（任意）</div>
            <select
              className="select"
              value={babaCode}
              onChange={(e) => {
                setBabaCode(e.target.value);
                setPage(1);
              }}
            >
              <option value="">すべて</option>
              {venues.map((v) => (
                <option key={v.baba_code} value={String(v.baba_code)}>
                  {v.baba_code} - {v.venue_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <div className="small">1ページの表示件数</div>
            <select
              className="select"
              value={String(pageSize)}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="500">500</option>
            </select>
          </label>

          <button className="btn" onClick={() => qEntries.refetch()}>
            更新
          </button>
        </div>
      </div>

      {qVenues.isLoading ? <div className="small">競馬場を読み込み中…</div> : null}
      {qVenues.error ? <ErrorBox error={qVenues.error} /> : null}

      {qEntries.isLoading ? <Loading label="出走表を読み込み中…" /> : null}
      {qEntries.error ? <ErrorBox error={qEntries.error} /> : null}

      {qEntries.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">
              出走馬一覧（{qEntries.data.items.length}件） / {qEntries.data.page}ページ / 1ページ{qEntries.data.page_size}件
            </h2>
            <div className="row">
              <button className="btn" disabled={!canPrev} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                前のページ
              </button>
              <button className="btn" disabled={!canNext} onClick={() => setPage((p) => p + 1)}>
                次のページ
              </button>
            </div>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>競馬場コード</th>
                <th>レース番号</th>
                <th>発走時刻</th>
                <th>レースID</th>
                <th>馬番</th>
                <th>馬名</th>
                <th>騎手</th>
                <th>斤量（kg）</th>
                <th>馬体重（kg）</th>
              </tr>
            </thead>
            <tbody>
              {qEntries.data.items.map((e) => (
                <tr key={e.race_entry_id}>
                  <td>{e.race_key.baba_code}</td>
                  <td>{e.race_key.race_no}</td>
                  <td>{e.start_time || ""}</td>
                  <td>
                    <Link to={`/races/${e.race_id}`}>{e.race_id}</Link>
                  </td>
                  <td>{e.horse_number}</td>
                  <td>{e.horse_name}</td>
                  <td>{e.jockey_name || ""}</td>
                  <td>{e.handicap_kg ?? ""}</td>
                  <td>
                    {e.body_weight ?? ""}
                    {e.body_weight_diff != null ? ` (${e.body_weight_diff >= 0 ? "+" : ""}${e.body_weight_diff})` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

