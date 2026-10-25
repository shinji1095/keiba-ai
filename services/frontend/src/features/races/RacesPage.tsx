import React from "react";
import { statusLabel } from "@/shared/labels";
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

export function RacesPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const [raceDate, setRaceDate] = React.useState(todayIsoDate());
  const [babaCode, setBabaCode] = React.useState<string>("");

  const qVenues = useQuery({
    queryKey: ["venues"],
    queryFn: () => api.listVenues(ctx),
  });
  const venues = mergeVenues(qVenues.data?.items);

  const qRaces = useQuery({
    queryKey: ["races", raceDate, babaCode],
    queryFn: () =>
      api.listRaces(ctx, {
        race_date: raceDate,
        baba_code: babaCode ? Number(babaCode) : undefined,
        page: 1,
        page_size: 200,
      }),
  });

  return (
    <div>
      <h1 className="pageTitle">レース一覧</h1>
      <p className="pageDesc">開催日や競馬場を指定してレースを検索できます。</p>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <label>
            <div className="small">開催日</div>
            <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
          </label>

          <label>
            <div className="small">競馬場（任意）</div>
            <select className="select" value={babaCode} onChange={(e) => setBabaCode(e.target.value)}>
              <option value="">すべて</option>
              {venues.map((v) => (
                <option key={v.baba_code} value={String(v.baba_code)}>
                  {v.baba_code} - {v.venue_name}
                </option>
              ))}
            </select>
          </label>

          <button className="btn" onClick={() => qRaces.refetch()}>
            検索
          </button>
        </div>

        {qVenues.isLoading ? <div className="small" style={{ marginTop: 8 }}>競馬場を読み込み中…</div> : null}
        {qVenues.error ? <div style={{ marginTop: 8 }}><ErrorBox error={qVenues.error} /></div> : null}
      </div>

      {qRaces.isLoading ? <Loading label="レースを読み込み中…" /> : null}
      {qRaces.error ? <ErrorBox error={qRaces.error} /> : null}

      {qRaces.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">レース一覧 ({qRaces.data.items.length})</h2>
            <button className="btn" onClick={() => qRaces.refetch()}>
              更新
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>レースID</th>
                <th>開催日</th>
                <th>競馬場コード</th>
                <th>レース番号</th>
                <th>発走時刻</th>
                <th>レース名</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              {qRaces.data.items.map((r) => (
                <tr key={r.race_id}>
                  <td>
                    <Link to={`/races/${r.race_id}`}>{r.race_id}</Link>
                  </td>
                  <td>{r.race_key.race_date}</td>
                  <td>{r.race_key.baba_code}</td>
                  <td>{r.race_key.race_no}</td>
                  <td>{r.start_time || ""}</td>
                  <td>{r.race_name || ""}</td>
                  <td>{statusLabel(r.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
