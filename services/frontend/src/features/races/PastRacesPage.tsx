import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { mergeVenues } from "@/shared/venues";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

function yesterdayIsoDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

export function PastRacesPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const [raceDate, setRaceDate] = React.useState(yesterdayIsoDate());
  const [babaCode, setBabaCode] = React.useState<string>("");
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(200);

  const qVenues = useQuery({
    queryKey: ["venues"],
    queryFn: () => api.listVenues(ctx),
  });
  const venues = mergeVenues(qVenues.data?.items);

  const qEntryResults = useQuery({
    queryKey: ["race-entry-results", raceDate, babaCode, page, pageSize],
    queryFn: () =>
      api.listRaceEntryResultsByDate(ctx, {
        race_date: raceDate,
        baba_code: babaCode ? Number(babaCode) : undefined,
        page,
        page_size: pageSize,
      }),
  });

  const canPrev = page > 1;
  const canNext = (qEntryResults.data?.items.length ?? 0) === pageSize;

  return (
    <div>
      <h1 className="pageTitle">過去のレース</h1>
      <p className="pageDesc">開催日を選んで、過去のレースの出走表と競走成績を確認できます。</p>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <label>
            <div className="small">開催日</div>
            <input
              className="input"
              type="date"
              value={raceDate}
              onChange={(e) => {
                setRaceDate(e.target.value);
                setPage(1);
              }}
            />
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

          <button className="btn" onClick={() => qEntryResults.refetch()}>
            更新
          </button>
        </div>
      </div>

      {qVenues.isLoading ? <div className="small">競馬場を読み込み中…</div> : null}
      {qVenues.error ? <ErrorBox error={qVenues.error} /> : null}

      {qEntryResults.isLoading ? <Loading label="出走表と成績を読み込み中…" /> : null}
      {qEntryResults.error ? <ErrorBox error={qEntryResults.error} /> : null}

      {qEntryResults.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">
              出走馬・成績一覧（{qEntryResults.data.items.length}件） / {qEntryResults.data.page}ページ / 1ページ{qEntryResults.data.page_size}件
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
                <th>着順</th>
                <th>馬番</th>
                <th>馬名</th>
                <th>騎手</th>
                <th>斤量（kg）</th>
                <th>馬体重（kg）</th>
                <th>走破タイム</th>
                <th>人気</th>
              </tr>
            </thead>
            <tbody>
              {qEntryResults.data.items.map((e) => (
                <tr key={e.race_entry_id}>
                  <td>{e.race_key.baba_code}</td>
                  <td>{e.race_key.race_no}</td>
                  <td>{e.start_time || ""}</td>
                  <td>
                    <Link to={`/races/${e.race_id}`}>{e.race_id}</Link>
                  </td>
                  <td>{e.finish_position ?? ""}</td>
                  <td>{e.horse_number}</td>
                  <td>{e.horse_name}</td>
                  <td>{e.jockey_name || ""}</td>
                  <td>{e.handicap_kg ?? ""}</td>
                  <td>
                    {e.body_weight ?? ""}
                    {e.body_weight_diff != null ? ` (${e.body_weight_diff >= 0 ? "+" : ""}${e.body_weight_diff})` : ""}
                  </td>
                  <td>{e.time_str ?? ""}</td>
                  <td>{e.popularity ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

