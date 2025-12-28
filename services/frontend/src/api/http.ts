import { ErrorEnvelope } from "./generated";

export class ApiHttpError extends Error {
  public readonly status: number;
  public readonly payload?: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = "ApiHttpError";
    this.status = status;
    this.payload = payload;
  }
}

export function getApiBaseUrl(): string {
  const v = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return (v && v.trim()) || "/api";
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("/")) {
    if (typeof window !== "undefined" && window.location?.origin) {
      return `${window.location.origin}${trimmed}`;
    }
  }
  return trimmed;
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, unknown>): string {
  const normalized = normalizeBaseUrl(baseUrl);
  const base = normalized.endsWith("/") ? normalized : `${normalized}/`;
  const safePath = path.startsWith("/") ? path.slice(1) : path;
  const url = new URL(safePath, base);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function tryParseJson(res: Response): Promise<unknown | undefined> {
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return undefined;
  try {
    return await res.json();
  } catch {
    return undefined;
  }
}

function errorMessageFromEnvelope(payload: unknown): string | undefined {
  const env = payload as Partial<ErrorEnvelope> | undefined;
  const err = env?.error as any;
  if (err && typeof err.message === "string") return err.message;
  return undefined;
}

export type UnauthorizedHandler = () => Promise<string | null>;

export async function apiFetch<T>(args: {
  baseUrl: string;
  path: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  token?: string | null;
  query?: Record<string, unknown>;
  body?: unknown;
  signal?: AbortSignal;
  onUnauthorized?: UnauthorizedHandler;
  retryOnUnauthorized?: boolean;
}): Promise<T> {
  const url = buildUrl(args.baseUrl, args.path, args.query);

  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (args.body !== undefined) headers["Content-Type"] = "application/json";
  if (args.token) headers["Authorization"] = `Bearer ${args.token}`;

  const res = await fetch(url, {
    method: args.method,
    headers,
    body: args.body !== undefined ? JSON.stringify(args.body) : undefined,
    credentials: "include",
    signal: args.signal,
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const payload = await tryParseJson(res);

  if (res.ok) {
    return payload as T;
  }

  if (res.status === 401 && args.onUnauthorized && (args.retryOnUnauthorized ?? true)) {
    const newToken = await args.onUnauthorized();
    if (newToken) {
      return await apiFetch<T>({ ...args, token: newToken, retryOnUnauthorized: false });
    }
  }

  const msg = errorMessageFromEnvelope(payload) || `HTTP ${res.status}`;
  throw new ApiHttpError(msg, res.status, payload);
}
