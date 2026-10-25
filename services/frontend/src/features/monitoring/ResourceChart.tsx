import React from "react";
import { HistoryPoint, MetricHistory } from "@/api/monitoring";
import { bytes, jst, chartPaths } from "./chartUtils";

type Series = { key: string; label: string; color: string };
type Marker = { at: string; label: string; color: string };
type Props = {
  title: string;
  history?: MetricHistory;
  series: Series[];
  percent?: boolean;
  threshold?: number;
  markers?: Marker[];
  activeAt: string | null;
  onActiveAt: (at: string | null) => void;
  mode: "average" | "max";
};

export function ResourceChart({
  title,
  history,
  series,
  percent,
  threshold,
  markers = [],
  activeAt,
  onActiveAt,
  mode,
}: Props) {
  const id = React.useId().replaceAll(":", "");
  const points = history?.points ?? [];
  const start = history ? Date.parse(history.start) : 0,
    end = history ? Date.parse(history.end) : 1;
  const field = mode === "max" ? "max_values" : "values";
  const values = points.flatMap((p) =>
    series.map((s) => p[field][s.key]).filter((v): v is number => v != null),
  );
  const maximum = percent ? 100 : Math.max(1024, ...values) * 1.15;
  const active = activeAt
    ? points.reduce<HistoryPoint | null>(
        (best, p) =>
          !best ||
          Math.abs(Date.parse(p.at) - Date.parse(activeAt)) <
            Math.abs(Date.parse(best.at) - Date.parse(activeAt))
            ? p
            : best,
        null,
      )
    : null;
  const visibleMarkers = markers.filter(
    (m) => Date.parse(m.at) >= start && Date.parse(m.at) <= end,
  );
  const format = (value: number | null | undefined) =>
    value == null ? "—" : percent ? `${value.toFixed(1)}%` : `${bytes(value)}/s`;
  const hasValues = values.length > 0;
  function move(event: React.PointerEvent<SVGSVGElement>) {
    if (!points.length) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const at =
      start +
      Math.max(0, Math.min(1, (((event.clientX - rect.left) / rect.width) * 800 - 48) / 704)) *
        (end - start);
    onActiveAt(new Date(at).toISOString());
  }
  function keyboard(event: React.KeyboardEvent) {
    if (!points.length || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const index = active ? points.indexOf(active) : points.length - 1;
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? points.length - 1
          : Math.max(0, Math.min(points.length - 1, index + (event.key === "ArrowLeft" ? -1 : 1)));
    onActiveAt(points[next].at);
  }
  return (
    <section className="card monitorChart">
      <div className="cardHeader">
        <h2 className="cardTitle">{title}</h2>
        <span className="small">
          {mode === "max" ? "区間最大" : "区間平均"} · {percent ? "%" : "転送量 / 秒"}
        </span>
      </div>
      <div className="monitorLegend">
        {series.map((s) => (
          <span key={s.key}>
            <i style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
      <div className="monitorPlot">
        <svg
          viewBox="0 0 800 220"
          role="img"
          aria-labelledby={`${id}-title ${id}-desc`}
          tabIndex={0}
          onPointerMove={move}
          onPointerLeave={() => onActiveAt(null)}
          onKeyDown={keyboard}
          onFocus={() => {
            if (!activeAt && points.length) onActiveAt(points[points.length - 1].at);
          }}
        >
          <title id={`${id}-title`}>{title}の推移グラフ</title>
          <desc id={`${id}-desc`}>日本時間。欠測は空白表示。左右キーで計測値を確認できます。</desc>
          {[0, 25, 50, 75, 100].map((tick) => {
            const y = 186 - (tick / 100) * 160;
            return (
              <g key={tick}>
                <line x1="48" x2="752" y1={y} y2={y} stroke="var(--border)" strokeDasharray="3 5" />
                <text x="40" y={y + 4} textAnchor="end" className="monitorAxis">
                  {percent ? tick : bytes((maximum * tick) / 100)}
                </text>
              </g>
            );
          })}
          {threshold != null && (
            <g>
              <line
                x1="48"
                x2="752"
                y1={186 - threshold * 1.6}
                y2={186 - threshold * 1.6}
                stroke="#f5bd5a"
                strokeDasharray="6 5"
              />
              <text x="748" y={180 - threshold * 1.6} textAnchor="end" className="monitorAxis">
                注意 {threshold}%
              </text>
            </g>
          )}
          <defs>
            <clipPath id={`${id}-clip`}>
              <rect x="48" y="15" width="704" height="175" />
            </clipPath>
          </defs>
          <g clipPath={`url(#${id}-clip)`}>
            {visibleMarkers.map((marker, i) => (
              <line
                key={i}
                x1={48 + ((Date.parse(marker.at) - start) / (end - start)) * 704}
                x2={48 + ((Date.parse(marker.at) - start) / (end - start)) * 704}
                y1="26"
                y2="186"
                stroke={marker.color}
                opacity="0.55"
                strokeDasharray="2 4"
              >
                <title>
                  {jst(marker.at, true)} {marker.label}
                </title>
              </line>
            ))}
            {series.flatMap((s) =>
              chartPaths(
                points,
                s.key,
                field,
                start,
                end,
                maximum,
                history?.resolution_sec ?? 10,
              ).map((path, i) => (
                <path
                  key={`${s.key}-${i}`}
                  d={path}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )),
            )}
            {active && (
              <line
                x1={48 + ((Date.parse(active.at) - start) / (end - start)) * 704}
                x2={48 + ((Date.parse(active.at) - start) / (end - start)) * 704}
                y1="26"
                y2="186"
                stroke="var(--muted)"
              />
            )}
          </g>
          {[0, 0.25, 0.5, 0.75, 1].map((part) => (
            <text
              key={part}
              x={48 + part * 704}
              y="210"
              textAnchor="middle"
              className="monitorAxis"
            >
              {history
                ? jst(
                    new Date(start + (end - start) * part).toISOString(),
                    end - start > 86_400_000,
                  )
                : "—"}
            </text>
          ))}
        </svg>
        {!hasValues && <div className="monitorChartEmpty">計測データがありません</div>}
      </div>
      <div className="monitorChartReadout" aria-live="polite">
        <span>{active ? jst(active.at, true) : "グラフ上にカーソルを合わせて詳細を表示"}</span>
        {active &&
          series.map((s) => (
            <span key={s.key} style={{ color: s.color }}>
              {s.label}: {format(active[field][s.key])}
            </span>
          ))}
      </div>
    </section>
  );
}

export function ResourceGauge({
  label,
  value,
  color,
  detail,
}: {
  label: string;
  value: number | null;
  color: string;
  detail: string;
}) {
  const safe = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <article className="card monitorGauge">
      <div className="monitorGaugeRing">
        <svg
          viewBox="0 0 120 120"
          role="img"
          aria-label={`${label} ${value == null ? "データなし" : value.toFixed(1) + "%"}`}
        >
          <circle cx="60" cy="60" r="49" fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx="60"
            cy="60"
            r="49"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={`${(safe / 100) * 308} 308`}
            strokeLinecap="round"
            transform="rotate(-90 60 60)"
          />
        </svg>
        <strong>
          {value == null ? "—" : value.toFixed(1)}
          <small>{value == null ? "" : "%"}</small>
        </strong>
      </div>
      <div>
        <h2>{label}</h2>
        <p>{detail}</p>
      </div>
    </article>
  );
}
