import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
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
      <h1 className="pageTitle">Races</h1>
      <p className="pageDesc">/races (GET): 日付・競馬場コードでレースを一覧します。</p>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <label>
            <div className="small">race_date</div>
            <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
          </label>

          <label>
            <div className="small">baba_code (optional)</div>
            <select className="select" value={babaCode} onChange={(e) => setBabaCode(e.target.value)}>
              <option value="">(all)</option>
              {qVenues.data?.items.map((v) => (
                <option key={v.baba_code} value={String(v.baba_code)}>
                  {v.baba_code} - {v.venue_name}
                </option>
              ))}
            </select>
          </label>

          <button className="btn" onClick={() => qRaces.refetch()}>
            Search
          </button>
        </div>

        {qVenues.isLoading ? <div className="small" style={{ marginTop: 8 }}>Loading venues...</div> : null}
        {qVenues.error ? <div style={{ marginTop: 8 }}><ErrorBox error={qVenues.error} /></div> : null}
      </div>

      {qRaces.isLoading ? <Loading label="Loading races..." /> : null}
      {qRaces.error ? <ErrorBox error={qRaces.error} /> : null}

      {qRaces.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">items ({qRaces.data.items.length})</h2>
            <button className="btn" onClick={() => qRaces.refetch()}>
              Refresh
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>race_id</th>
                <th>race_date</th>
                <th>baba_code</th>
                <th>race_no</th>
                <th>start_time</th>
                <th>race_name</th>
                <th>status</th>
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
                  <td>{r.status || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
