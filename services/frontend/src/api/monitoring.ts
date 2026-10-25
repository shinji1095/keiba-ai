import { ApiCtx } from "./endpoints";
import { apiFetch } from "./http";

export type DiskMetric = {
  path: string;
  label: string;
  total_bytes: number;
  used_bytes: number;
  available_bytes: number;
  percent: number;
};
export type MetricSample = {
  host_id: string;
  hostname: string;
  scope: "host" | "vm" | "container";
  sampled_at: string;
  uptime_sec: number;
  cpu_count: number;
  cpu_percent: number | null;
  cpu_per_core: (number | null)[];
  memory_total_bytes: number;
  memory_available_bytes: number;
  memory_percent: number;
  swap_total_bytes: number;
  swap_used_bytes: number;
  disks: DiskMetric[];
  net_rx_bytes_sec: number | null;
  net_tx_bytes_sec: number | null;
  disk_read_bytes_sec: number | null;
  disk_write_bytes_sec: number | null;
  temperature_c: number | null;
  errors: string[];
  temperature_sensor?: string | null;
  network_interfaces?: string[];
};
export type MonitorEvent = {
  id: string;
  resource: string;
  level: string;
  message: string;
  started_at: string;
  resolved_at: string | null;
};
export type MetricStatus = {
  status: string;
  sample: MetricSample | null;
  age_sec: number | null;
  server_time: string;
  alerts: MonitorEvent[];
  thresholds: { cpu: number[]; memory: number[]; disk: number[] };
};
export type HistoryPoint = {
  at: string;
  values: Record<string, number | null>;
  max_values: Record<string, number | null>;
  sample_counts: Record<string, number>;
};
export type MetricHistory = {
  host_id: string | null;
  start: string;
  end: string;
  resolution_sec: number;
  points: HistoryPoint[];
};
export type ScrapeJob = {
  id: string;
  worker: string;
  status: string;
  target: {
    race_date?: string;
    baba_code?: number;
    race_no?: number;
    race_key?: { race_date: string; baba_code: number; race_no?: number };
    page_name?: string;
    task_kind?: string;
    snapshot_kind?: string;
  };
  started_at: string;
  finished_at: string | null;
  progress_at: string;
  saved_items: number;
  attempts: number;
  error: string | null;
  note?: string;
  delayed?: boolean;
  worker_alive?: boolean;
};
export type JobList = { items: ScrapeJob[]; total: number; page: number; page_size: number };
export type ScrapeStatus = {
  connection: string;
  error?: string;
  workers?: {
    name: string;
    alive: boolean;
    heartbeat_at?: string;
    age_sec: number | null;
    phase?: string;
  }[];
  schedule?: { enabled: boolean; baba_codes: number[] };
  running?: ScrapeJob[];
  progress?: {
    total: number;
    completed: number;
    counts: Record<string, number>;
    next_at: string | null;
    plan_available: boolean;
    overdue?: number;
  };
  sync?: {
    last_synced_at?: string | null;
    last_attempted_at?: string | null;
    last_status?: string | null;
    last_error?: string | null;
    next_scheduled_at?: string | null;
  } | null;
};

function get<T>(ctx: ApiCtx, path: string, query?: Record<string, unknown>, signal?: AbortSignal) {
  return apiFetch<T>({ ...ctx, path, method: "GET", query, signal });
}
export const monitoringApi = {
  metrics: (ctx: ApiCtx, signal?: AbortSignal) =>
    get<MetricStatus>(ctx, "/system/metrics", undefined, signal),
  history: (ctx: ApiCtx, hours: number, signal?: AbortSignal) =>
    get<MetricHistory>(ctx, "/system/metrics/history", { hours }, signal),
  events: (ctx: ApiCtx, signal?: AbortSignal) =>
    get<{ items: MonitorEvent[] }>(ctx, "/system/events", undefined, signal),
  status: (ctx: ApiCtx, signal?: AbortSignal) =>
    get<ScrapeStatus>(ctx, "/scrape/status", undefined, signal),
  jobs: (ctx: ApiCtx, query: Record<string, unknown>, signal?: AbortSignal) =>
    get<JobList>(ctx, "/scrape/jobs", query, signal),
};
