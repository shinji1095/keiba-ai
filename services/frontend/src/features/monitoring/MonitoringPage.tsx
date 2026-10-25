import React from "react";
import { scrapeTargetLabel, snapshotKindLabel } from "@/shared/labels";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { monitoringApi, ScrapeJob } from "@/api/monitoring";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { VENUE_MASTER } from "@/shared/venues";
import { ResourceChart, ResourceGauge } from "./ResourceChart";
import { bytes, jst } from "./chartUtils";
import "./monitoring.css";

const labels: Record<string, string> = {
  ok: "正常",
  unknown: "未計測",
  unavailable: "監視不能",
  stale: "情報遅延",
  warning: "注意",
  critical: "異常",
  running: "実行中",
  planned: "待機",
  success: "成功",
  failed: "失敗",
  retrying: "再試行待ち",
  skipped: "スキップ",
  interrupted: "中断",
};
const colors: Record<string, string> = {
  success: "#39d98a",
  skipped: "#92a3c3",
  running: "#5aa3ff",
  planned: "#33435e",
  retrying: "#f5bd5a",
  failed: "#ff6b6b",
  interrupted: "#d899ff",
};
function todayJst() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" }).format(new Date());
}
function venueName(code?: number) {
  return code == null
    ? "—"
    : (VENUE_MASTER.find((v) => v.baba_code === code)?.venue_name ?? `場コード ${code}`);
}
function target(job: ScrapeJob) {
  const race = job.target.race_key ?? job.target;
  return `${race.race_date ?? ""} ${venueName(race.baba_code)} ${race.race_no ? `${race.race_no}R` : "全レース"} ${scrapeTargetLabel(job.target.page_name ?? "")}`;
}
function duration(job: ScrapeJob) {
  const seconds = Math.max(
    0,
    Math.floor(
      ((job.finished_at ? Date.parse(job.finished_at) : Date.now()) - Date.parse(job.started_at)) /
        1000,
    ),
  );
  return `${Math.floor(seconds / 60)}分 ${seconds % 60}秒`;
}
function Badge({ status, text }: { status: string; text?: string }) {
  return (
    <span className={`monitorBadge ${status}`}>
      <i />
      {text ?? labels[status] ?? status}
    </span>
  );
}

export function MonitoringPage() {
  const ctx = useApiCtx();
  const [hours, setHours] = React.useState(1);
  const [auto, setAuto] = React.useState(true);
  const [mode, setMode] = React.useState<"average" | "max">("average");
  const [activeAt, setActiveAt] = React.useState<string | null>(null);
  const [raceDate, setRaceDate] = React.useState(todayJst);
  const [babaCode, setBabaCode] = React.useState("");
  const [jobStatus, setJobStatus] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [visible, setVisible] = React.useState(!document.hidden);
  React.useEffect(() => {
    const listener = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", listener);
    return () => document.removeEventListener("visibilitychange", listener);
  }, []);
  const options = {
    refetchInterval: auto && visible ? 10_000 : (false as const),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: auto,
    retry: false as const,
  };
  const rootKey = ["monitoring", ctx.baseUrl, ctx.token];
  const metrics = useQuery({
    ...options,
    queryKey: [...rootKey, "metrics"],
    queryFn: ({ signal }) => monitoringApi.metrics(ctx, signal),
  });
  const history = useQuery({
    ...options,
    queryKey: [...rootKey, "history", hours],
    queryFn: ({ signal }) => monitoringApi.history(ctx, hours, signal),
  });
  const status = useQuery({
    ...options,
    queryKey: [...rootKey, "status"],
    queryFn: ({ signal }) => monitoringApi.status(ctx, signal),
  });
  const events = useQuery({
    ...options,
    queryKey: [...rootKey, "events"],
    queryFn: ({ signal }) => monitoringApi.events(ctx, signal),
  });
  const jobQuery = {
    race_date: raceDate || undefined,
    baba_code: babaCode || undefined,
    status: jobStatus || undefined,
    page,
  };
  const jobs = useQuery({
    ...options,
    queryKey: [...rootKey, "jobs", jobQuery],
    queryFn: ({ signal }) => monitoringApi.jobs(ctx, jobQuery, signal),
  });
  React.useEffect(() => {
    if (visible && auto)
      void Promise.all([
        metrics.refetch(),
        history.refetch(),
        status.refetch(),
        events.refetch(),
        jobs.refetch(),
      ]);
    // Refetch on tab return; other changes are handled by query keys and polling.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, auto]);
  const sample = metrics.data?.sample;
  const progress = status.data?.progress;
  const scheduler = status.data?.workers?.find((w) => w.name === "scheduler");
  const monitorState = metrics.isError ? "unavailable" : (metrics.data?.status ?? "unknown");
  const scraperState =
    status.isError || status.data?.connection === "unavailable"
      ? "unavailable"
      : scheduler
        ? scheduler.alive
          ? progress?.overdue ||
            progress?.counts.retrying ||
            status.data?.running?.some((job) => job.delayed)
            ? "warning"
            : "ok"
          : "critical"
        : "unknown";
  const diskPercent = sample?.disks.length ? Math.max(...sample.disks.map((d) => d.percent)) : null;
  const updatedAt = Math.max(metrics.dataUpdatedAt, status.dataUpdatedAt);
  const refresh = () => {
    void Promise.all([
      metrics.refetch(),
      history.refetch(),
      status.refetch(),
      events.refetch(),
      jobs.refetch(),
    ]);
  };
  const markers = [
    ...(events.data?.items ?? []).map((e) => ({
      at: e.started_at,
      label: e.message,
      color: e.level === "critical" ? "#ff6b6b" : "#f5bd5a",
    })),
    ...(jobs.data?.items ?? [])
      .filter((j) => j.error)
      .map((j) => ({
        at: j.finished_at ?? j.started_at,
        label: `取得失敗: ${target(j)}`,
        color: "#d899ff",
      })),
    ...(status.data?.sync?.last_status === "failed" && status.data.sync.last_attempted_at
      ? [{ at: status.data.sync.last_attempted_at, label: "DB同期失敗", color: "#ff6b6b" }]
      : []),
  ];
  const chartProps = { history: history.data, activeAt, onActiveAt: setActiveAt, mode, markers };
  const total = progress?.total ?? 0;
  const complete = progress?.completed ?? 0;
  const slices = Object.entries(progress?.counts ?? {}).filter(([name]) => name in colors);
  const knownDone = (progress?.counts.success ?? 0) + (progress?.counts.skipped ?? 0);
  if (complete > knownDone) slices.push(["success", complete - knownDone]);
  const sum = slices.reduce((acc, [, count]) => acc + count, 0);
  let offset = 0;

  return (
    <div className="monitorPage">
      <header className="monitorHeader">
        <div>
          <div className="monitorEyebrow">稼働モニター</div>
          <h1 className="pageTitle">スクレイピング・PC稼働状況</h1>
          <p className="pageDesc">PCの余力とデータ収集の進み具合を、ひとつの画面で。</p>
        </div>
        <div className="monitorControls">
          <label className="small">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />{" "}
            10秒ごとに更新
          </label>
          <button
            className="btn"
            onClick={refresh}
            disabled={metrics.isFetching || status.isFetching}
          >
            更新
          </button>
        </div>
      </header>
      {[metrics, status, history].some((q) => q.isError) && (
        <div className="alert" role="alert">
          最新情報を取得できません。表示中の値は前回取得時点の情報です。接続とログイン状態を確認してください。
        </div>
      )}
      <section className="card monitorSummary">
        <div>
          <span className="small">PCリソース</span>
          <Badge status={monitorState} />
          <strong>{sample?.hostname ?? "計測データを待っています"}</strong>
          <span className="small">
            {sample
              ? `${sample.host_id} · ${{ host: "実行PC全体", vm: "仮想マシン全体", container: "コンテナ内" }[sample.scope]}`
              : "ホスト計測の接続後に表示されます"}
          </span>
        </div>
        <div>
          <span className="small">スクレイピング</span>
          <Badge status={scraperState} />
          <strong>
            {status.data?.schedule
              ? status.data.schedule.enabled
                ? "自動取得 有効"
                : "自動取得 無効"
              : "状態を確認中"}
          </strong>
          <span className="small">スケジューラ最終応答 {jst(scheduler?.heartbeat_at)}</span>
          <span className="small">
            制御API: {status.data?.connection === "ok" ? "接続済み" : "未接続"}
          </span>
        </div>
        <div className="monitorTimes">
          <span>最終計測 {jst(sample?.sampled_at)}</span>
          <span>画面取得 {updatedAt ? jst(new Date(updatedAt).toISOString()) : "—"}</span>
          <span>すべて日本時間（JST）</span>
        </div>
      </section>
      {metrics.data?.alerts.length ? (
        <div className="monitorAlerts">
          {metrics.data.alerts.map((event) => (
            <div className="alert" key={event.id}>
              <strong>{event.level === "critical" ? "異常" : "注意"}</strong> · {event.message}{" "}
              <span className="small">{jst(event.started_at, true)}〜</span>
            </div>
          ))}
        </div>
      ) : null}
      <div className="monitorGauges" aria-busy={metrics.isPending}>
        <ResourceGauge
          label="CPU使用率"
          value={sample?.cpu_percent ?? null}
          color="#5aa3ff"
          detail={sample ? `${sample.cpu_count}論理CPU · 全体を100%として表示` : "未計測"}
        />
        <ResourceGauge
          label="メモリ使用率"
          value={sample?.memory_percent ?? null}
          color="#b393ff"
          detail={
            sample
              ? `${bytes(sample.memory_total_bytes - sample.memory_available_bytes)} / ${bytes(sample.memory_total_bytes)}`
              : "未計測"
          }
        />
        <ResourceGauge
          label="ディスク使用率"
          value={diskPercent}
          color="#39d9b4"
          detail={sample?.disks.length ? "監視対象の最大使用率" : "未計測"}
        />
      </div>
      <section className="monitorHistoryHeader">
        <div>
          <h2>リソースの推移</h2>
          <p className="small">欠測は空白表示 · 黄色は注意閾値 · 縦線は警告／取得失敗の発生時刻</p>
        </div>
        <div className="monitorControls">
          <div className="monitorSegments" role="group" aria-label="グラフ期間">
            {[
              [1, "1時間"],
              [24, "24時間"],
              [168, "7日"],
            ].map(([value, label]) => (
              <button
                key={value}
                aria-pressed={hours === value}
                onClick={() => {
                  setHours(Number(value));
                  setActiveAt(null);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="small">
            集計{" "}
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as "average" | "max")}
              aria-label="グラフ集計方法"
            >
              <option value="average">平均</option>
              <option value="max">最大</option>
            </select>
          </label>
        </div>
      </section>
      {history.isPending && (
        <p className="small" role="status">
          グラフを読み込んでいます…
        </p>
      )}
      <div className="monitorChartGrid">
        <ResourceChart
          {...chartProps}
          title="CPU使用率"
          series={[{ key: "cpu_percent", label: "CPU", color: "#5aa3ff" }]}
          percent
          threshold={metrics.data?.thresholds.cpu[0]}
        />
        <ResourceChart
          {...chartProps}
          title="メモリ使用率"
          series={[{ key: "memory_percent", label: "メモリ", color: "#b393ff" }]}
          percent
          threshold={metrics.data?.thresholds.memory[0]}
        />
        <ResourceChart
          {...chartProps}
          title="ディスク使用率"
          series={[{ key: "disk_percent", label: "保存先の最大使用率", color: "#39d9b4" }]}
          percent
          threshold={metrics.data?.thresholds.disk[0]}
        />
        <ResourceChart
          {...chartProps}
          title="ネットワーク転送量"
          series={[
            { key: "net_rx_bytes_sec", label: "受信", color: "#5aa3ff" },
            { key: "net_tx_bytes_sec", label: "送信", color: "#f5bd5a" },
          ]}
        />
        <ResourceChart
          {...chartProps}
          title="ディスクI/O"
          series={[
            { key: "disk_read_bytes_sec", label: "読込", color: "#39d9b4" },
            { key: "disk_write_bytes_sec", label: "書込", color: "#b393ff" },
          ]}
        />
        <section className="card monitorHardware">
          <h2 className="cardTitle">PCの詳細</h2>
          <dl>
            <dt>稼働時間</dt>
            <dd>
              {sample
                ? `${Math.floor(sample.uptime_sec / 86400)}日 ${Math.floor(sample.uptime_sec / 3600) % 24}時間 ${Math.floor(sample.uptime_sec / 60) % 60}分`
                : "—"}
            </dd>
            <dt>利用可能メモリ</dt>
            <dd>{bytes(sample?.memory_available_bytes)}</dd>
            <dt>OS起動日時</dt>
            <dd>
              {sample
                ? jst(
                    new Date(
                      Date.parse(sample.sampled_at) - sample.uptime_sec * 1000,
                    ).toISOString(),
                    true,
                  )
                : "—"}
            </dd>
            <dt>スワップ</dt>
            <dd>
              {sample
                ? sample.swap_total_bytes
                  ? `${bytes(sample.swap_used_bytes)} / ${bytes(sample.swap_total_bytes)} (${((sample.swap_used_bytes / sample.swap_total_bytes) * 100).toFixed(1)}%)`
                  : "未設定"
                : "—"}
            </dd>
            <dt>CPU温度</dt>
            <dd>
              {sample
                ? sample.temperature_c == null
                  ? "非対応"
                  : `${sample.temperature_c.toFixed(1)} °C ${sample.temperature_sensor ?? ""}`
                : "—"}
            </dd>
            <dt>通信インターフェース</dt>
            <dd>{sample?.network_interfaces?.join(", ") || "—"}</dd>
          </dl>
          <details>
            <summary>コア別CPU使用率</summary>
            <div className="monitorCoreGrid">
              {sample?.cpu_per_core.map((value, index) => (
                <div key={index}>
                  <span>CPU {index}</span>
                  <meter min="0" max="100" value={value ?? 0} aria-label={`CPU ${index}`} />
                  <strong>{value == null ? "—" : `${value.toFixed(0)}%`}</strong>
                </div>
              ))}
            </div>
          </details>
          {sample?.errors.length ? (
            <div className="small">
              {sample.errors.map((error, i) => (
                <p key={i}>{error}</p>
              ))}
            </div>
          ) : null}
        </section>
      </div>
      <section className="card">
        <div className="cardHeader">
          <h2 className="cardTitle">保存先の容量</h2>
          <span className="small">同じファイルシステムはまとめて表示</span>
        </div>
        <div className="monitorTableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>保存先</th>
                <th>使用状況</th>
                <th>使用量 / 総容量</th>
                <th>空き容量</th>
              </tr>
            </thead>
            <tbody>
              {sample?.disks.map((disk) => (
                <tr key={disk.path}>
                  <td>
                    <strong>{disk.label}</strong>
                    <div className="small">{disk.path}</div>
                  </td>
                  <td>
                    <div className="monitorDiskBar">
                      <span
                        style={{
                          width: `${disk.percent}%`,
                          background:
                            disk.percent >= (metrics.data?.thresholds.disk[1] ?? 90)
                              ? "#ff6b6b"
                              : "#39d9b4",
                        }}
                      />
                    </div>
                    {disk.percent.toFixed(1)}%
                  </td>
                  <td>
                    {bytes(disk.used_bytes)} / {bytes(disk.total_bytes)}
                  </td>
                  <td>{bytes(disk.available_bytes)}</td>
                </tr>
              ))}
              {!sample?.disks.length && (
                <tr>
                  <td colSpan={4}>計測データがありません</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <div className="monitorChartGrid">
        <section className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">本日の取得進捗</h2>
            <Link className="small" to="/scrape-schedule">
              実行予定を見る →
            </Link>
          </div>
          <div className="monitorProgress">
            <div className="monitorProgressRing">
              <svg
                viewBox="0 0 160 160"
                role="img"
                aria-label={`本日の取得進捗 ${complete} / ${total}件完了`}
              >
                <circle
                  cx="80"
                  cy="80"
                  r="65"
                  fill="none"
                  stroke="var(--border)"
                  strokeWidth="12"
                />
                {slices.map(([name, count], i) => {
                  const length = sum ? (count / sum) * 408.4 : 0;
                  const dashOffset = -offset;
                  offset += length;
                  return (
                    <circle
                      key={i}
                      cx="80"
                      cy="80"
                      r="65"
                      fill="none"
                      stroke={colors[name]}
                      strokeWidth="12"
                      strokeDasharray={`${length} 408.4`}
                      strokeDashoffset={dashOffset}
                      transform="rotate(-90 80 80)"
                    />
                  );
                })}
              </svg>
              <div>
                <strong>
                  {total ? Math.round((complete / total) * 100) : "—"}
                  <small>{total ? "%" : ""}</small>
                </strong>
                <span>
                  {complete} / {total} 件完了
                </span>
              </div>
            </div>
            <div className="monitorProgressLegend">
              {Object.entries(colors).map(([name, color]) => (
                <div key={name}>
                  <i style={{ background: color }} />
                  {labels[name]}
                  <strong>{progress?.counts[name] ?? 0}</strong>
                </div>
              ))}
            </div>
          </div>
          <p className="small">
            {progress?.plan_available
              ? total
                ? `次回予定 ${jst(progress.next_at)}`
                : "本日の取得対象はありません"
              : "本日の計画はまだ生成されていません"}
          </p>
          {progress?.overdue ? (
            <p className="alert">許容時間を超えた未完了の取得が {progress.overdue} 件あります。</p>
          ) : null}
          {status.data?.running?.map((job) => (
            <div className="monitorRunning" key={job.id}>
              <Badge
                status={job.worker_alive ? (job.delayed ? "warning" : "running") : "critical"}
                text={
                  job.worker_alive ? (job.delayed ? "処理遅延" : "実行中") : "実行プロセス応答なし"
                }
              />
              <strong>{target(job)}</strong>
              <span className="small">
                {job.worker === "manual" ? "手動" : "定期"} · 開始 {jst(job.started_at)} · 経過{" "}
                {duration(job)} · 保存 {job.saved_items}件
              </span>
            </div>
          ))}
        </section>
        <section className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">DB同期</h2>
            <Badge
              status={
                status.data?.sync?.last_status === "success"
                  ? "ok"
                  : status.data?.sync?.last_status === "failed"
                    ? "critical"
                    : "unknown"
              }
              text={
                status.data?.sync?.last_status === "success"
                  ? "同期成功"
                  : status.data?.sync?.last_status === "failed"
                    ? "同期失敗"
                    : "未実行 / 待機"
              }
            />
          </div>
          <dl className="monitorSync">
            <dt>最終成功</dt>
            <dd>{jst(status.data?.sync?.last_synced_at, true)}</dd>
            <dt>次回予定</dt>
            <dd>{jst(status.data?.sync?.next_scheduled_at, true)}</dd>
          </dl>
          {status.data?.sync?.last_error && <p className="alert">{status.data.sync.last_error}</p>}
          <Link className="btn" to="/scrape">
            取得・同期の操作画面へ
          </Link>
          <p className="small">取得データの保存とDBへの反映は、それぞれの状態で確認できます。</p>
        </section>
      </div>
      <section className="card">
        <div className="cardHeader">
          <h2 className="cardTitle">取得の実行履歴</h2>
          <span className="small">{jobs.data?.total ?? 0}件</span>
        </div>
        <div className="monitorFilters">
          <label>
            対象日
            <input
              type="date"
              value={raceDate}
              onChange={(e) => {
                setRaceDate(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            競馬場
            <select
              value={babaCode}
              onChange={(e) => {
                setBabaCode(e.target.value);
                setPage(1);
              }}
            >
              <option value="">すべて</option>
              {VENUE_MASTER.map((v) => (
                <option key={v.baba_code} value={v.baba_code}>
                  {v.venue_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            結果
            <select
              value={jobStatus}
              onChange={(e) => {
                setJobStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">すべて</option>
              {Object.keys(colors)
                .filter((k) => k !== "planned")
                .map((k) => (
                  <option key={k} value={k}>
                    {labels[k]}
                  </option>
                ))}
            </select>
          </label>
        </div>
        {jobs.isError && <p className="alert">実行履歴を取得できません。</p>}
        <div className="monitorTableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>開始 / 終了（JST）</th>
                <th>対象</th>
                <th>状態</th>
                <th>処理時間</th>
                <th>試行 / 保存件数</th>
                <th>詳細</th>
              </tr>
            </thead>
            <tbody>
              {jobs.data?.items.map((job) => (
                <tr key={job.id}>
                  <td>
                    {jst(job.started_at, true)}
                    <div className="small">{jst(job.finished_at)}</div>
                  </td>
                  <td>
                    {target(job)}
                    <div className="small">
                      {job.worker === "manual" ? "手動" : "定期"} · {snapshotKindLabel(job.target.snapshot_kind ?? "")}
                    </div>
                  </td>
                  <td>
                    <Badge status={job.status} />
                  </td>
                  <td>{duration(job)}</td>
                  <td>
                    {job.attempts}回 / {job.saved_items}件
                  </td>
                  <td>
                    {job.error ? (
                      <details>
                        <summary>エラーを見る</summary>
                        <p>{job.error}</p>
                        <span className="small">ID: {job.id}</span>
                      </details>
                    ) : (
                      (job.note ?? "—")
                    )}
                  </td>
                </tr>
              ))}
              {!jobs.isPending && !jobs.data?.items.length && (
                <tr>
                  <td colSpan={6}>条件に一致する実行履歴はありません</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="monitorPagination">
          <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            前へ
          </button>
          <span className="small">{page}ページ</span>
          <button
            className="btn"
            disabled={!jobs.data || page * jobs.data.page_size >= jobs.data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            次へ
          </button>
        </div>
      </section>
      <section className="card">
        <div className="cardHeader">
          <h2 className="cardTitle">PC警告の履歴</h2>
          <span className="small">直近100件 · 取得失敗は上の実行履歴に表示</span>
        </div>
        {events.isError && <p className="alert">警告履歴を取得できません。</p>}
        <div className="monitorEventList">
          {events.data?.items.map((event) => (
            <div key={event.id}>
              <Badge status={event.level} />
              <time>{jst(event.started_at, true)}</time>
              <span>{event.message}</span>
              <span className="small">
                {event.resolved_at ? `解除 ${jst(event.resolved_at, true)}` : "継続中"}
              </span>
            </div>
          ))}
          {!events.data?.items.length && <p className="small">警告履歴はありません</p>}
        </div>
      </section>
    </div>
  );
}
