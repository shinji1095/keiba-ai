import React from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { BetType, SnapshotKind } from "@/api/generated";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

const betTypes: BetType[] = [
  "tansho",
  "fukusho",
  "wakuren",
  "wakutan",
  "umaren",
  "umatan",
  "wide",
  "sanrenpuku",
  "sanrentan",
];

const snapshotKinds: SnapshotKind[] = ["t_minus_5m", "t_minus_1m", "final"];

type TabKey = "summary" | "entries" | "odds" | "results" | "payouts";

export function RaceDetailPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const params = useParams();
  const raceId = Number(params.raceId);

  const [tab, setTab] = React.useState<TabKey>("summary");
  const [betType, setBetType] = React.useState<BetType>("tansho");
  const [snapshotKind, setSnapshotKind] = React.useState<SnapshotKind>("final");

  const qRace = useQuery({
    queryKey: ["race", raceId],
    queryFn: () => api.getRace(ctx, raceId),
    enabled: Number.isFinite(raceId),
  });

  const qEntries = useQuery({
    queryKey: ["raceEntries", raceId],
    queryFn: () => api.listRaceEntries(ctx, raceId),
    enabled: tab === "entries" && Number.isFinite(raceId),
  });

  const qOdds = useQuery({
    queryKey: ["raceOdds", raceId, snapshotKind, betType],
    queryFn: () => api.getRaceOdds(ctx, raceId, { snapshot_kind: snapshotKind, bet_type: betType }),
    enabled: tab === "odds" && Number.isFinite(raceId),
  });

  const qResults = useQuery({
    queryKey: ["raceResults", raceId],
    queryFn: () => api.listRaceResults(ctx, raceId),
    enabled: tab === "results" && Number.isFinite(raceId),
  });

  const qPayouts = useQuery({
    queryKey: ["racePayouts", raceId],
    queryFn: () => api.listRacePayouts(ctx, raceId),
    enabled: tab === "payouts" && Number.isFinite(raceId),
  });

  return (
    <div>
      <h1 className="pageTitle">Race Detail</h1>
      <p className="pageDesc">/races/{"{race_id}"} (GET) と関連エンドポイント</p>

      {!Number.isFinite(raceId) ? <div className="alert">Invalid race_id</div> : null}

      {qRace.isLoading ? <Loading label="Loading race..." /> : null}
      {qRace.error ? <ErrorBox error={qRace.error} /> : null}

      {qRace.data ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">
              race_id={qRace.data.race_id} / {qRace.data.race_key.race_date} / baba={qRace.data.race_key.baba_code} /
              no={qRace.data.race_key.race_no}
            </h2>
            <span className="pill">{qRace.data.status || "unknown"}</span>
          </div>

          <div className="row" style={{ gap: 10 }}>
            <span className="pill">start {qRace.data.start_time || "-"}</span>
            <span className="pill">distance {qRace.data.distance_m ?? "-"}</span>
            <span className="pill">course {qRace.data.course ?? "-"}</span>
            <span className="pill">weather {qRace.data.weather ?? "-"}</span>
            <span className="pill">track {qRace.data.track_condition ?? "-"}</span>
            <span className="pill">field {qRace.data.field_size ?? "-"}</span>
          </div>

          <div style={{ marginTop: 10 }}>{qRace.data.race_name || ""}</div>
        </div>
      ) : null}

      <div className="row" style={{ marginBottom: 12 }}>
        {(["summary", "entries", "odds", "results", "payouts"] as TabKey[]).map((k) => (
          <button key={k} className={tab === k ? "btn primary" : "btn"} onClick={() => setTab(k)}>
            {k}
          </button>
        ))}
      </div>

      {tab === "summary" ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Summary</h2>
          </div>
          {qRace.data ? (
            <table className="table">
              <tbody>
                <tr>
                  <th>race_id</th>
                  <td>{qRace.data.race_id}</td>
                </tr>
                <tr>
                  <th>race_key</th>
                  <td>
                    {qRace.data.race_key.race_date} / baba={qRace.data.race_key.baba_code} / no={qRace.data.race_key.race_no}
                  </td>
                </tr>
                <tr>
                  <th>start_time</th>
                  <td>{qRace.data.start_time || ""}</td>
                </tr>
                <tr>
                  <th>race_name</th>
                  <td>{qRace.data.race_name || ""}</td>
                </tr>
                <tr>
                  <th>status</th>
                  <td>{qRace.data.status || ""}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="small">No data.</div>
          )}
        </div>
      ) : null}

      {tab === "entries" ? (
        <div>
          {qEntries.isLoading ? <Loading label="Loading entries..." /> : null}
          {qEntries.error ? <ErrorBox error={qEntries.error} /> : null}
          {qEntries.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">Entries ({qEntries.data.items.length})</h2>
                <button className="btn" onClick={() => qEntries.refetch()}>
                  Refresh
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>post</th>
                    <th>no</th>
                    <th>horse</th>
                    <th>jockey</th>
                    <th>trainer</th>
                    <th>handicap_kg</th>
                    <th>body_weight</th>
                    <th>diff</th>
                  </tr>
                </thead>
                <tbody>
                  {qEntries.data.items.map((e) => (
                    <tr key={e.race_entry_id}>
                      <td>{e.post_position ?? ""}</td>
                      <td>{e.horse_number}</td>
                      <td>{e.horse_name}</td>
                      <td>{e.jockey_name ?? ""}</td>
                      <td>{e.trainer_name ?? ""}</td>
                      <td>{e.handicap_kg ?? ""}</td>
                      <td>{e.body_weight ?? ""}</td>
                      <td>{e.body_weight_diff ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === "odds" ? (
        <div>
          <div className="card" style={{ marginBottom: 14 }}>
            <div className="row">
              <label>
                <div className="small">snapshot_kind</div>
                <select className="select" value={snapshotKind} onChange={(e) => setSnapshotKind(e.target.value as SnapshotKind)}>
                  {snapshotKinds.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <div className="small">bet_type</div>
                <select className="select" value={betType} onChange={(e) => setBetType(e.target.value as BetType)}>
                  {betTypes.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </label>

              <button className="btn" onClick={() => qOdds.refetch()}>
                Fetch odds
              </button>
            </div>

            <div className="small" style={{ marginTop: 10 }}>
              /races/{{race_id}}/odds?snapshot_kind=...&bet_type=...
            </div>
          </div>

          {qOdds.isLoading ? <Loading label="Loading odds..." /> : null}
          {qOdds.error ? <ErrorBox error={qOdds.error} /> : null}

          {qOdds.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">
                  Odds ({qOdds.data.snapshot.snapshot_kind}, {qOdds.data.snapshot.bet_type}) items={qOdds.data.items.length}
                </h2>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>legs</th>
                    <th>ordered</th>
                    <th>odds_min</th>
                    <th>odds_max</th>
                    <th>popularity</th>
                    <th>raw</th>
                  </tr>
                </thead>
                <tbody>
                  {qOdds.data.items.slice(0, 300).map((it) => (
                    <tr key={it.odds_item_id}>
                      <td>{it.legs.join("-")}</td>
                      <td>{it.is_ordered ? "true" : "false"}</td>
                      <td>{it.odds_min ?? ""}</td>
                      <td>{it.odds_max ?? ""}</td>
                      <td>{it.popularity ?? ""}</td>
                      <td>{it.raw_text ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {qOdds.data.items.length > 300 ? (
                <div className="small" style={{ marginTop: 10 }}>
                  表示は先頭 300 件に制限しています（items={qOdds.data.items.length}）。
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === "results" ? (
        <div>
          {qResults.isLoading ? <Loading label="Loading results..." /> : null}
          {qResults.error ? <ErrorBox error={qResults.error} /> : null}

          {qResults.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">Results ({qResults.data.items.length})</h2>
                <button className="btn" onClick={() => qResults.refetch()}>
                  Refresh
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>finish_position</th>
                    <th>horse_no</th>
                    <th>frame_no</th>
                    <th>time</th>
                    <th>margin</th>
                    <th>pop</th>
                    <th>odds</th>
                  </tr>
                </thead>
                <tbody>
                  {qResults.data.items.map((r) => (
                    <tr key={r.race_result_id}>
                      <td>{r.finish_position ?? ""}</td>
                      <td>{r.horse_number ?? ""}</td>
                      <td>{r.frame_number ?? ""}</td>
                      <td>{r.time_str ?? ""}</td>
                      <td>{r.margin_str ?? ""}</td>
                      <td>{r.popularity ?? ""}</td>
                      <td>{r.odds ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === "payouts" ? (
        <div>
          {qPayouts.isLoading ? <Loading label="Loading payouts..." /> : null}
          {qPayouts.error ? <ErrorBox error={qPayouts.error} /> : null}

          {qPayouts.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">Payouts ({qPayouts.data.items.length})</h2>
                <button className="btn" onClick={() => qPayouts.refetch()}>
                  Refresh
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>bet_type</th>
                    <th>legs</th>
                    <th>payout_yen</th>
                    <th>popularity</th>
                  </tr>
                </thead>
                <tbody>
                  {qPayouts.data.items.map((p) => (
                    <tr key={p.payout_id}>
                      <td>{p.bet_type}</td>
                      <td>{p.legs.join("-")}</td>
                      <td>{p.payout_yen}</td>
                      <td>{p.popularity ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
