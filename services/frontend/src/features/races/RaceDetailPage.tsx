import React from "react";
import { betTypeLabel, snapshotKindLabel, statusLabel } from "@/shared/labels";
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

const tabLabels: Record<TabKey, string> = {
  summary: "レース概要",
  entries: "出走表",
  odds: "オッズ",
  results: "競走成績",
  payouts: "払戻金",
};

type OddsTrendPoint = {
  snapshot_kind: SnapshotKind;
  captured_at: string;
  odds_min: number | null;
  odds_max: number | null;
  popularity: number | null;
};

type OddsTrendSeries = {
  horse_no: number;
  points: OddsTrendPoint[];
};

type OddsTrendSnapshot = {
  snapshot_kind: SnapshotKind;
  captured_at: string;
  by_horse_no: Record<number, Pick<OddsTrendPoint, "odds_min" | "odds_max" | "popularity">>;
};

type OddsTrendAll = {
  bet_type: BetType;
  snapshots: OddsTrendSnapshot[];
  series: OddsTrendSeries[];
};

const trendKinds: SnapshotKind[] = ["t_minus_60m", "t_minus_30m", "t_minus_5m", "t_minus_1m", "final"];

function colorForHorseNo(horseNo: number): string {
  const hue = (horseNo * 37) % 360;
  return `hsl(${hue} 80% 65%)`;
}

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
    queryKey: ["raceOddsTrendAll", raceId, trendBetType],
    queryFn: async (): Promise<OddsTrendAll> => {
      if (!trendSupported) return { bet_type: trendBetType, snapshots: [], series: [] };
      const snapshots: OddsTrendSnapshot[] = [];
      for (const kind of trendKinds) {
        try {
          const res = await api.getRaceOdds(ctx, raceId, { snapshot_kind: kind, bet_type: trendBetType });
          const byHorseNo: OddsTrendSnapshot["by_horse_no"] = {};
          for (const it of res.items) {
            if (it.legs.length !== 1) continue;
            const horseNo = it.legs[0];
            if (!Number.isFinite(horseNo)) continue;
            byHorseNo[horseNo] = {
              odds_min: it.odds_min ?? null,
              odds_max: it.odds_max ?? null,
              popularity: it.popularity ?? null,
            };
          }
          snapshots.push({
            snapshot_kind: res.snapshot.snapshot_kind,
            captured_at: res.snapshot.captured_at,
            by_horse_no: byHorseNo,
          });
        } catch (err) {
          if (err instanceof ApiHttpError && err.status === 404) continue;
          throw err;
        }
      }

      const horseNosSet = new Set<number>();
      for (const s of snapshots) {
        for (const k of Object.keys(s.by_horse_no)) {
          const horseNo = Number(k);
          if (Number.isFinite(horseNo)) horseNosSet.add(horseNo);
        }
      }
      const horseNos = [...horseNosSet].sort((a, b) => a - b);
      const series: OddsTrendSeries[] = horseNos.map((horseNo) => ({
        horse_no: horseNo,
        points: snapshots.map((s) => ({
          snapshot_kind: s.snapshot_kind,
          captured_at: s.captured_at,
          odds_min: s.by_horse_no[horseNo]?.odds_min ?? null,
          odds_max: s.by_horse_no[horseNo]?.odds_max ?? null,
          popularity: s.by_horse_no[horseNo]?.popularity ?? null,
        })),
      }));

      return { bet_type: trendBetType, snapshots, series };
    },
    enabled: tab === "odds" && Number.isFinite(raceId) && trendSupported,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
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
      <h1 className="pageTitle">レース詳細</h1>
      <p className="pageDesc">レース概要・出走表・オッズ・競走成績・払戻金を確認できます。</p>

      {!Number.isFinite(raceId) ? <div className="alert">レースIDが正しくありません。</div> : null}

      {qRace.isLoading ? <Loading label="レース情報を読み込み中…" /> : null}
      {qRace.error ? <ErrorBox error={qRace.error} /> : null}

      {qRace.data ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">
              レースID：{qRace.data.race_id} / {qRace.data.race_key.race_date} / 競馬場コード：{qRace.data.race_key.baba_code} /
              第{qRace.data.race_key.race_no}レース
            </h2>
            <span className="pill">{statusLabel(qRace.data.status)}</span>
          </div>

          <div className="row" style={{ gap: 10 }}>
            <span className="pill">発走時刻 {qRace.data.start_time || "-"}</span>
            <span className="pill">距離 {qRace.data.distance_m ?? "-"}m</span>
            <span className="pill">コース {qRace.data.course ?? "-"}</span>
            <span className="pill">天候 {qRace.data.weather ?? "-"}</span>
            <span className="pill">馬場状態 {qRace.data.track_condition ?? "-"}</span>
            <span className="pill">出走頭数 {qRace.data.field_size ?? "-"}頭</span>
          </div>

          <div style={{ marginTop: 10 }}>{qRace.data.race_name || ""}</div>
        </div>
      ) : null}

      <div className="row" style={{ marginBottom: 12 }}>
        {(["summary", "entries", "odds", "results", "payouts"] as TabKey[]).map((k) => (
          <button key={k} className={tab === k ? "btn primary" : "btn"} onClick={() => setTab(k)}>
            {tabLabels[k]}
          </button>
        ))}
      </div>

      {tab === "summary" ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">レース概要</h2>
          </div>
          {qRace.data ? (
            <table className="table">
              <tbody>
                <tr>
                  <th>レースID</th>
                  <td>{qRace.data.race_id}</td>
                </tr>
                <tr>
                  <th>開催日・競馬場・レース番号</th>
                  <td>
                    {qRace.data.race_key.race_date} / 競馬場コード：{qRace.data.race_key.baba_code} / 第{qRace.data.race_key.race_no}レース
                  </td>
                </tr>
                <tr>
                  <th>発走時刻</th>
                  <td>{qRace.data.start_time || ""}</td>
                </tr>
                <tr>
                  <th>レース名</th>
                  <td>{qRace.data.race_name || ""}</td>
                </tr>
                <tr>
                  <th>状態</th>
                  <td>{statusLabel(qRace.data.status)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="small">データがありません。</div>
          )}
        </div>
      ) : null}

      {tab === "entries" ? (
        <div>
          {qEntries.isLoading ? <Loading label="出走表を読み込み中…" /> : null}
          {qEntries.error ? <ErrorBox error={qEntries.error} /> : null}
          {qSpecCard.isLoading ? <Loading label="出走馬の詳細を読み込み中…" /> : null}
          {showSpecError ? <ErrorBox error={qSpecCard.error} /> : null}
          {qEntries.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">出走表 ({qEntries.data.items.length})</h2>
                <button className="btn" onClick={() => qEntries.refetch()}>
                  更新
                </button>
              </div>

              {qSpecCard.data ? (
                <div className="small" style={{ marginBottom: 10 }}>
                  出走馬の詳細データを取得済みです。
                </div>
              ) : (
                <div className="small" style={{ marginBottom: 10 }}>
                  出走馬の詳細データはまだありません。
                </div>
              )}

              <table className="table">
                <thead>
                  <tr>
                    <th></th>
                    <th>枠番</th>
                    <th>馬番</th>
                    <th>馬名</th>
                    <th>騎手</th>
                    <th>調教師</th>
                    <th>斤量（kg）</th>
                    <th>馬体重（kg）</th>
                    <th>馬体重増減（kg）</th>
                    <th>通算成績</th>
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
                                <span className="pill">通算 {perfLabel(perfTotal)}</span>
                                <span className="pill">左回り {perfLabel(perfLeft)}</span>
                                <span className="pill">右回り {perfLabel(perfRight)}</span>
                                <span className="pill">当競馬場 {perfLabel(perfTrack)}</span>
                                <span className="pill">同距離 {perfLabel(perfDistance)}</span>
                              </div>

                              {last5.length ? (
                                <table className="table">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      <th>開催日</th>
                                      <th>競馬場</th>
                                      <th>距離（m）</th>
                                      <th>着順</th>
                                      <th>頭数</th>
                                      <th>走破タイム</th>
                                      <th>タイム差</th>
                                      <th>人気</th>
                                      <th>馬体重（kg）</th>
                                      <th>騎手</th>
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
                                <div className="small">直近5走のデータがありません。</div>
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
                <div className="small">取得タイミング</div>
                <select className="select" value={snapshotKind} onChange={(e) => setSnapshotKind(e.target.value as SnapshotKind)}>
                  {snapshotKinds.map((k) => (
                    <option key={k} value={k}>
                      {snapshotKindLabel(k)}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <div className="small">券種</div>
                <select className="select" value={betType} onChange={(e) => setBetType(e.target.value as BetType)}>
                  {betTypes.map((k) => (
                    <option key={k} value={k}>
                      {betTypeLabel(k)}
                    </option>
                  ))}
                </select>
              </label>

              <button className="btn" onClick={() => qOdds.refetch()}>
                オッズを取得
              </button>
            </div>

            <div className="small" style={{ marginTop: 10 }}>
              取得タイミングと券種を選んでオッズを確認できます。
            </div>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <div className="cardHeader">
              <h2 className="cardTitle">全馬のオッズ推移</h2>
              <button className="btn" onClick={() => qOddsTrend.refetch()}>
                更新
              </button>
            </div>

            <div className="row">
              <label>
                <div className="small">グラフの券種</div>
                <select className="select" value={trendBetType} onChange={(e) => setTrendBetType(e.target.value as BetType)}>
                  {(["tansho", "fukusho"] as BetType[]).map((k) => (
                    <option key={k} value={k}>
                      {betTypeLabel(k)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {!trendSupported ? <div className="small">オッズ推移は単勝・複勝に対応しています。</div> : null}
            {qOddsTrend.isFetching ? <Loading label="オッズ推移を読み込み中…" /> : null}
            {qOddsTrend.error ? <ErrorBox error={qOddsTrend.error} /> : null}

            {qOddsTrend.data ? (
              qOddsTrend.data.snapshots.length ? (
                (() => {
                  const snapshots = qOddsTrend.data.snapshots;
                  const series = qOddsTrend.data.series;

                  const w = 720;
                  const h = 260;
                  const padL = 40;
                  const padR = 14;
                  const padT = 14;
                  const padB = 44;
                  const innerW = w - padL - padR;
                  const innerH = h - padT - padB;

                  const yValues: number[] = [];
                  for (const s of series) {
                    for (const p of s.points) {
                      const v = p.odds_min ?? p.odds_max;
                      if (typeof v === "number" && Number.isFinite(v)) yValues.push(v);
                    }
                  }
                  const yMin = yValues.length ? Math.min(...yValues) : 0;
                  const yMax = yValues.length ? Math.max(...yValues) : 0;
                  const yLo = yMin === yMax ? yMin - 1 : yMin;
                  const yHi = yMin === yMax ? yMax + 1 : yMax;

                  const xAt = (i: number) => padL + (innerW * i) / Math.max(1, snapshots.length - 1);
                  const yAt = (v: number) => padT + innerH * (1 - (v - yLo) / (yHi - yLo));
                  const label = snapshotKindLabel;

                  const paths = series.map((s) => {
                    const d: string[] = [];
                    let open = false;
                    for (let i = 0; i < s.points.length; i++) {
                      const p = s.points[i];
                      const v = p.odds_min ?? p.odds_max;
                      if (typeof v !== "number" || !Number.isFinite(v)) {
                        open = false;
                        continue;
                      }
                      const cmd = open ? "L" : "M";
                      d.push(`${cmd}${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`);
                      open = true;
                    }
                    return { horse_no: s.horse_no, d: d.join(" ") };
                  });

                  return (
                    <div style={{ marginTop: 12 }}>
                      {yValues.length ? (
                        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: h, display: "block" }}>
                          <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="rgba(170,182,214,0.5)" strokeWidth="1" />
                          <line
                            x1={padL}
                            y1={padT + innerH}
                            x2={padL + innerW}
                            y2={padT + innerH}
                            stroke="rgba(170,182,214,0.5)"
                            strokeWidth="1"
                          />

                          {paths.map((p) =>
                            p.d ? (
                              <path
                                key={p.horse_no}
                                d={p.d}
                                fill="none"
                                stroke={colorForHorseNo(p.horse_no)}
                                strokeWidth="1.6"
                                strokeOpacity="0.9"
                              />
                            ) : null,
                          )}

                          {snapshots.map((s, i) => (
                            <text
                              key={s.snapshot_kind}
                              x={xAt(i)}
                              y={padT + innerH + 28}
                              fill="rgba(170,182,214,0.9)"
                              fontSize="12"
                              textAnchor="middle"
                            >
                              {label(s.snapshot_kind)}
                            </text>
                          ))}

                          <text x={0} y={padT + 12} fill="rgba(170,182,214,0.9)" fontSize="12">
                            {yHi.toFixed(1)}
                          </text>
                          <text x={0} y={padT + innerH} fill="rgba(170,182,214,0.9)" fontSize="12">
                            {yLo.toFixed(1)}
                          </text>
                        </svg>
                      ) : (
                        <div className="small">グラフに表示できるオッズがありません。</div>
                      )}

                      {series.length ? (
                        <div className="row" style={{ gap: 8, marginTop: 10 }}>
                          {series.map((s) => (
                            <span key={s.horse_no} className="pill" style={{ borderColor: colorForHorseNo(s.horse_no), color: colorForHorseNo(s.horse_no) }}>
                              {s.horse_no}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })()
              ) : (
                <div className="small" style={{ marginTop: 10 }}>
                  オッズ推移のデータがありません。
                </div>
              )
            ) : null}
          </div>

          {qOdds.isLoading ? <Loading label="オッズを読み込み中…" /> : null}
          {qOdds.error ? <ErrorBox error={qOdds.error} /> : null}

          {qOdds.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">
                  オッズ（{snapshotKindLabel(qOdds.data.snapshot.snapshot_kind)}・{betTypeLabel(qOdds.data.snapshot.bet_type)}） 件数：{qOdds.data.items.length}
                </h2>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>組み合わせ</th>
                    <th>着順指定</th>
                    {isTansho ? <th>オッズ</th> : <th>オッズ下限</th>}
                    {isTansho ? null : <th>オッズ上限</th>}
                    <th>人気</th>
                    <th>取得元の表記</th>
                  </tr>
                </thead>
                <tbody>
                  {qOdds.data.items.slice(0, 300).map((it) => (
                    <tr key={it.odds_item_id}>
                      <td>{it.legs.join("-")}</td>
                      <td>{it.is_ordered ? "あり" : "なし"}</td>
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
                  表示は先頭 300 件に制限しています（全{qOdds.data.items.length}件）。
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === "results" ? (
        <div>
          {qResults.isLoading ? <Loading label="競走成績を読み込み中…" /> : null}
          {qResults.error ? <ErrorBox error={qResults.error} /> : null}

          {qResults.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">競走成績 ({qResults.data.items.length})</h2>
                <button className="btn" onClick={() => qResults.refetch()}>
                  更新
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>着順</th>
                    <th>馬番</th>
                    <th>走破タイム</th>
                    <th>着差</th>
                    <th>上がり3F</th>
                    <th>人気</th>
                    <th>1コーナー</th>
                    <th>2コーナー</th>
                    <th>3コーナー</th>
                    <th>4コーナー</th>
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
          {qPayouts.isLoading ? <Loading label="払戻金を読み込み中…" /> : null}
          {qPayouts.error ? <ErrorBox error={qPayouts.error} /> : null}

          {qPayouts.data ? (
            <div className="card">
              <div className="cardHeader">
                <h2 className="cardTitle">払戻金 ({qPayouts.data.items.length})</h2>
                <button className="btn" onClick={() => qPayouts.refetch()}>
                  更新
                </button>
              </div>

              <table className="table">
                <thead>
                  <tr>
                    <th>券種</th>
                    <th>組み合わせ</th>
                    <th>払戻金（円）</th>
                    <th>人気</th>
                  </tr>
                </thead>
                <tbody>
                  {qPayouts.data.items.map((p) => (
                    <tr key={p.payout_id}>
                      <td>{betTypeLabel(p.bet_type)}</td>
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
