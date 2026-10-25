import { HistoryPoint } from "@/api/monitoring";

export function jst(value?: string | null, date = false): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    ...(date ? { month: "2-digit", day: "2-digit" } : {}),
    hour: "2-digit",
    minute: "2-digit",
    second: date ? undefined : "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function bytes(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  if (value < 1024) return `${value.toFixed(0)} B`;
  const power = Math.min(4, Math.floor(Math.log(value) / Math.log(1024)));
  return `${(value / 1024 ** power).toFixed(1)} ${["B", "KiB", "MiB", "GiB", "TiB"][power]}`;
}

export function chartPaths(
  points: HistoryPoint[],
  key: string,
  field: "values" | "max_values",
  start: number,
  end: number,
  max: number,
  resolution: number,
): string[] {
  const paths: string[] = [];
  let path = "",
    previous = 0;
  for (const point of points) {
    const at = Date.parse(point.at),
      value = point[field][key];
    if (
      value == null ||
      !Number.isFinite(value) ||
      (previous && at - previous > resolution * 1500)
    ) {
      if (path) paths.push(path);
      path = "";
    }
    if (value != null && Number.isFinite(value)) {
      const x = 48 + ((at - start) / (end - start || 1)) * 704;
      const y = 186 - (Math.min(max, Math.max(0, value)) / max) * 160;
      path += `${path ? " L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
    }
    previous = at;
  }
  if (path) paths.push(path);
  return paths;
}
