import React from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { BetType, SnapshotKind, SpecPerf, SpecRaceCardResponse } from "@/api/generated";
import { ApiHttpError } from "@/api/http";
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

const snapshotKinds: SnapshotKind[] = ["t_minus_60m", "t_minus_30m", "t_minus_5m", "t_minus_1m", "final"];

type TabKey = "summary" | "entries" | "odds" | "results" | "payouts";

type OddsTrendPoint = {
  snapshot_kind: SnapshotKind;
  captured_at: string;
  odds_min: number | null;
  odds_max: number | null;
  popularity: number | null;
};

const trendKinds: SnapshotKind[] = ["t_minus_60m", "t_minus_30m", "t_minus_20m", "t_minus_10m", "t_minus_5m", "t_minus_1m", "final"];

function perfLabel(perf?: SpecPerf | null): string {
  if (!perf) return "-";
  return `${perf.first_cnt}-${perf.second_cnt}-${perf.third_cnt}-${perf.out_cnt} (${perf.starts})`;
}

function indexByHorseId<T extends { horse_id: number }>(items: T[]): Map<number, T> {
  return new Map(items.map((it) => [it.horse_id, it]));
}

function buildSpecEntryByHorseNo(card: SpecRaceCardResponse): Map<number, SpecRaceCardResponse["race_entries"][number]> {
  return new Map(card.race_entries.map((e) => [e.horse_no, e]));
}

export function RaceDetailPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const params = useParams();
  const raceId = Number(params.raceId);

  const [tab, setTab] = React.useState<TabKey>("summary");
  const [betType, setBetType] = React.useState<BetType>("tansho");
  const [snapshotKind, setSnapshotKind] = React.useState<SnapshotKind>("final");
  const [trendBetType, setTrendBetType] = React.useState<BetType>("tansho");
  const [trendHorseNo, setTrendHorseNo] = React.useState<number>(1);
  const isTansho = betType === "tansho";
  const trendSupported = trendBetType === "tansho" || trendBetType === "fukusho";

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

  const qOddsTrend = useQuery({
    queryKey: ["raceOddsTrend", raceId, trendBetType, trendHorseNo],
    queryFn: async (): Promise<OddsTrendPoint[]> => {
      if (!trendSupported) return [];
      const out: OddsTrendPoint[] = [];
      for (const kind of trendKinds) {
        try {
          const res = await api.getRaceOdds(ctx, raceId, { snapshot_kind: kind, bet_type: trendBetType });
          const item = res.items.find((it) => it.legs.length === 1 && it.legs[0] === trendHorseNo);
          out.push({
            snapshot_kind: kind,
            captured_at: res.snapshot.captured_at,
            odds_min: item?.odds_min ?? null,
            odds_max: item?.odds_max ?? null,
            popularity: item?.popularity ?? null,
          });
        } catch (err) {
          if (err instanceof ApiHttpError && err.status === 404) continue;
          throw err;
        }
      }
      return out;
    },
    enabled: false,
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

  const raceKey = qRace.data?.race_key;
  const qSpecCard = useQuery({
    queryKey: ["specRaceCard", raceKey?.race_date, raceKey?.baba_code, raceKey?.race_no],
    queryFn: () => api.getSpecRaceCard(ctx, raceKey!.baba_code, raceKey!.race_date, raceKey!.race_no),
    enabled: tab === "entries" && !!raceKey,
  });
  const showSpecError = qSpecCard.error && !(qSpecCard.error instanceof ApiHttpError && qSpecCard.error.status === 404);

  const [expandedHorseNos, setExpandedHorseNos] = React.useState<Set<number>>(new Set());
  const toggleHorse = (horseNo: number) => {
    setExpandedHorseNos((prev) => {
      const next = new Set(prev);
      if (next.has(horseNo)) next.delete(horseNo);
      else next.add(horseNo);
      return next;
    });
  };

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
          {qSpecCard.isLoading ? <Loading label="Loading spec race card..." /> : null}
          {showSpecError ? <ErrorBox error={qSpecCard.error} /> : null}
          {qEntries.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">Entries ({qEntries.data.items.length})</h2>
                <button className="btn" onClick={() => qEntries.refetch()}>
                  Refresh
                </button>
              </div>

              {qSpecCard.data ? (
                <div className="small" style={{ marginBottom: 10 }}>
                  spec: /spec/race-cards/{qSpecCard.data.race.baba_code}/{qSpecCard.data.race.race_date}/{qSpecCard.data.race.race_no}
                </div>
              ) : (
                <div className="small" style={{ marginBottom: 10 }}>
                  spec: (not available) /spec/race-cards/{"{baba_code}"}/{"{race_date}"}/{"{race_no}"}
                </div>
              )}

              <table className="table">
                <thead>
                  <tr>
                    <th></th>
                    <th>post</th>
                    <th>no</th>
                    <th>horse</th>
                    <th>jockey</th>
                    <th>trainer</th>
                    <th>handicap_kg</th>
                    <th>body_weight</th>
                    <th>diff</th>
                    <th>perf_total</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const card = qSpecCard.data;
                    if (!card) {
                      return qEntries.data.items.map((e) => (
                        <tr key={e.race_entry_id}>
                          <td></td>
                          <td>{e.post_position ?? ""}</td>
                          <td>{e.horse_number}</td>
                          <td>{e.horse_name}</td>
                          <td>{e.jockey_name ?? ""}</td>
                          <td>{e.trainer_name ?? ""}</td>
                          <td>{e.handicap_kg ?? ""}</td>
                          <td>{e.body_weight ?? ""}</td>
                          <td>{e.body_weight_diff ?? ""}</td>
                          <td>-</td>
                        </tr>
                      ));
                    }

                    const specEntryByNo = buildSpecEntryByHorseNo(card);
                    const perfTotalByHorseId = indexByHorseId(card.perf_total);
                    const perfLeftByHorseId = indexByHorseId(card.perf_dirt_left);
                    const perfRightByHorseId = indexByHorseId(card.perf_dirt_right);
                    const perfTrackByHorseId = indexByHorseId(card.perf_track);
                    const perfDistanceByHorseId = indexByHorseId(card.perf_distance);

                    const last5ByHorseNo = new Map<number, SpecRaceCardResponse["last5"]>();
                    for (const r of card.last5) {
                      const arr = last5ByHorseNo.get(r.horse_no) ?? [];
                      arr.push(r);
                      last5ByHorseNo.set(r.horse_no, arr);
                    }
                    for (const [k, arr] of last5ByHorseNo.entries()) {
                      arr.sort((a, b) => a.order_in_last5 - b.order_in_last5);
                      last5ByHorseNo.set(k, arr);
                    }

                    const colSpan = 10;
                    return qEntries.data.items.flatMap((e) => {
                      const horseNo = e.horse_number;
                      const specEntry = specEntryByNo.get(horseNo);
                      const horseId = specEntry?.horse_id ?? null;
                      const perfTotal = horseId ? perfTotalByHorseId.get(horseId) : null;
                      const isExpanded = expandedHorseNos.has(horseNo);
                      const last5 = last5ByHorseNo.get(horseNo) ?? [];
                      const detailsDisabled = !specEntry && last5.length === 0;

                      const mainRow = (
                        <tr key={e.race_entry_id}>
                          <td>
                            <button className="btn" disabled={detailsDisabled} onClick={() => toggleHorse(horseNo)}>
                              {isExpanded ? "−" : "+"}
                            </button>
                          </td>
                          <td>{e.post_position ?? ""}</td>
                          <td>{horseNo}</td>
                          <td>{e.horse_name}</td>
                          <td>{e.jockey_name ?? ""}</td>
                          <td>{e.trainer_name ?? ""}</td>
                          <td>{e.handicap_kg ?? ""}</td>
                          <td>{e.body_weight ?? ""}</td>
                          <td>{e.body_weight_diff ?? ""}</td>
                          <td>{perfLabel(perfTotal)}</td>
                        </tr>
                      );

                      if (!isExpanded) return [mainRow];

                      const perfLeft = horseId ? perfLeftByHorseId.get(horseId) : null;
                      const perfRight = horseId ? perfRightByHorseId.get(horseId) : null;
                      const perfTrack = horseId ? perfTrackByHorseId.get(horseId) : null;
                      const perfDistance = horseId ? perfDistanceByHorseId.get(horseId) : null;

                      const detailRow = (
                        <tr key={`${e.race_entry_id}-details`}>
                          <td colSpan={colSpan} style={{ paddingTop: 0 }}>
                            <div className="card" style={{ marginTop: 10, background: "rgba(15, 22, 38, 0.55)" }}>
                              <div className="cardHeader">
                                <h3 className="cardTitle">着別成績 / 競走成績（直近5走）</h3>
                              </div>

                              <div className="row" style={{ gap: 10, marginBottom: 12 }}>
                                <span className="pill">total {perfLabel(perfTotal)}</span>
                                <span className="pill">left {perfLabel(perfLeft)}</span>
                                <span className="pill">right {perfLabel(perfRight)}</span>
                                <span className="pill">track {perfLabel(perfTrack)}</span>
                                <span className="pill">distance {perfLabel(perfDistance)}</span>
                              </div>

                              {last5.length ? (
                                <table className="table">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      <th>date</th>
                                      <th>place</th>
                                      <th>dist</th>
                                      <th>pos</th>
                                      <th>runners</th>
                                      <th>time</th>
                                      <th>diff</th>
                                      <th>pop</th>
                                      <th>bw</th>
                                      <th>jockey</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {last5.map((r) => (
                                      <tr key={`${r.horse_no}-${r.order_in_last5}`}>
                                        <td>{r.order_in_last5}</td>
                                        <td>{r.past_race_date ?? ""}</td>
                                        <td>{r.place ?? ""}</td>
                                        <td>{r.distance_m ?? ""}</td>
                                        <td>{r.finish_pos ?? ""}</td>
                                        <td>{r.runners ?? ""}</td>
                                        <td>{r.time_raw ?? ""}</td>
                                        <td>{r.time_diff ?? ""}</td>
                                        <td>{r.popularity ?? ""}</td>
                                        <td>{r.body_weight ?? ""}</td>
                                        <td>{r.jockey_name ?? ""}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <div className="small">No last5 data.</div>
                              )}
                            </div>
                          </td>
                        </tr>
                      );

                      return [mainRow, detailRow];
                    });
                  })()}
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
              /races/{"{race_id}"}/odds?snapshot_kind=...&bet_type=...
            </div>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <div className="cardHeader">
              <h2 className="cardTitle">Odds Trend (graph)</h2>
              <button className="btn" onClick={() => qOddsTrend.refetch()}>
                Fetch trend
              </button>
            </div>

            <div className="row">
              <label>
                <div className="small">trend_type</div>
                <select className="select" value={trendBetType} onChange={(e) => setTrendBetType(e.target.value as BetType)}>
                  {(["tansho", "fukusho"] as BetType[]).map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <div className="small">horse_no</div>
                <input
                  className="input"
                  inputMode="numeric"
                  value={String(trendHorseNo)}
                  onChange={(e) => setTrendHorseNo(Number(e.target.value))}
                />
              </label>
            </div>

            {!trendSupported ? <div className="small">Trend is supported for tansho / fukusho only.</div> : null}
            {qOddsTrend.isFetching ? <Loading label="Loading odds trend..." /> : null}
            {qOddsTrend.error ? <ErrorBox error={qOddsTrend.error} /> : null}

            {qOddsTrend.data ? (
              qOddsTrend.data.length ? (
                (() => {
                  const points = qOddsTrend.data.filter((p) => typeof p.odds_min === "number") as Array<
                    OddsTrendPoint & { odds_min: number }
                  >;
                  const hasPlot = points.length > 0;
                  const w = 720;
                  const h = 220;
                  const padL = 40;
                  const padR = 14;
                  const padT = 14;
                  const padB = 34;
                  const innerW = w - padL - padR;
                  const innerH = h - padT - padB;
                  const ys = points.map((p) => p.odds_min);
                  const yMin = ys.length ? Math.min(...ys) : 0;
                  const yMax = ys.length ? Math.max(...ys) : 0;
                  const yLo = yMin === yMax ? yMin - 1 : yMin;
                  const yHi = yMin === yMax ? yMax + 1 : yMax;

                  const xAt = (i: number) => padL + (innerW * i) / Math.max(1, points.length - 1);
                  const yAt = (v: number) => padT + innerH * (1 - (v - yLo) / (yHi - yLo));

                  const poly = points.map((p, i) => `${xAt(i)},${yAt(p.odds_min)}`).join(" ");

                  const label = (k: string) => (k === "final" ? "final" : k.replace(/^t_minus_/, "T-"));

                  return (
                    <div style={{ marginTop: 12 }}>
                      {hasPlot ? (
                        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 220, display: "block" }}>
                          <line
                            x1={padL}
                            y1={padT}
                            x2={padL}
                            y2={padT + innerH}
                            stroke="rgba(170,182,214,0.5)"
                            strokeWidth="1"
                          />
                          <line
                            x1={padL}
                            y1={padT + innerH}
                            x2={padL + innerW}
                            y2={padT + innerH}
                            stroke="rgba(170,182,214,0.5)"
                            strokeWidth="1"
                          />

                          <polyline points={poly} fill="none" stroke="rgba(90, 163, 255, 0.95)" strokeWidth="2" />
                          {points.map((p, i) => (
                            <circle key={p.snapshot_kind} cx={xAt(i)} cy={yAt(p.odds_min)} r="3" fill="rgba(90, 163, 255, 0.95)" />
                          ))}

                          <text x={padL} y={padT + innerH + 26} fill="rgba(170,182,214,0.9)" fontSize="12">
                            {label(points[0].snapshot_kind)}
                          </text>
                          {points.length > 1 ? (
                            <text x={padL + innerW - 36} y={padT + innerH + 26} fill="rgba(170,182,214,0.9)" fontSize="12">
                              {label(points[points.length - 1].snapshot_kind)}
                            </text>
                          ) : null}

                          <text x={0} y={padT + 12} fill="rgba(170,182,214,0.9)" fontSize="12">
                            {yHi.toFixed(1)}
                          </text>
                          <text x={0} y={padT + innerH} fill="rgba(170,182,214,0.9)" fontSize="12">
                            {yLo.toFixed(1)}
                          </text>
                        </svg>
                      ) : (
                        <div className="small">No numeric odds to plot.</div>
                      )}

                      <table className="table">
                        <thead>
                          <tr>
                            <th>snapshot_kind</th>
                            <th>captured_at</th>
                            <th>odds_min</th>
                            <th>odds_max</th>
                            <th>popularity</th>
                          </tr>
                        </thead>
                        <tbody>
                          {qOddsTrend.data.map((p) => (
                            <tr key={p.snapshot_kind}>
                              <td>{p.snapshot_kind}</td>
                              <td>{p.captured_at}</td>
                              <td>{p.odds_min ?? ""}</td>
                              <td>{p.odds_max ?? ""}</td>
                              <td>{p.popularity ?? ""}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                })()
              ) : (
                <div className="small" style={{ marginTop: 10 }}>
                  No trend data.
                </div>
              )
            ) : null}
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
                    {isTansho ? <th>odds</th> : <th>odds_min</th>}
                    {isTansho ? null : <th>odds_max</th>}
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
                      {isTansho ? null : <td>{it.odds_max ?? ""}</td>}
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
                    <th>time</th>
                    <th>margin</th>
                    <th>last3f</th>
                    <th>popularity</th>
                    <th>corner1</th>
                    <th>corner2</th>
                    <th>corner3</th>
                    <th>corner4</th>
                  </tr>
                </thead>
                <tbody>
                  {qResults.data.items.map((r) => (
                    <tr key={r.race_result_id}>
                      <td>{r.finish_position ?? ""}</td>
                      <td>{r.horse_number ?? ""}</td>
                      <td>{r.time_str ?? ""}</td>
                      <td>{r.margin ?? ""}</td>
                      <td>{r.last3f ?? ""}</td>
                      <td>{r.popularity ?? ""}</td>
                      <td>{r.corner1 ?? ""}</td>
                      <td>{r.corner2 ?? ""}</td>
                      <td>{r.corner3 ?? ""}</td>
                      <td>{r.corner4 ?? ""}</td>
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
