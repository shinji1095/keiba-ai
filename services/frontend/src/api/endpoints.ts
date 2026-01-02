import {
  BatchUpsertResponse,
  BetType,
  ClientCredentialsTokenRequest,
  HealthResponse,
  ManualScrapeTaskRequest,
  ManualScrapeTaskResponse,
  OAuthClientCreateRequest,
  OAuthClientCreateResponse,
  OAuthClientListResponse,
  OAuthClientRotateSecretResponse,
  OAuthClientUpdateRequest,
  OAuthClientView,
  OddsSnapshotQueryResponse,
  OddsSnapshotUpsertRequest,
  OddsSnapshotUpsertResponse,
  PasswordLoginRequest,
  PayoutListResponse,
  PayoutUpsertBatchRequest,
  Race,
  RaceChangeInsertBatchRequest,
  RaceEntryListResponse,
  RaceEntryUpsertBatchRequest,
  RaceListResponse,
  RaceResultListResponse,
  RaceResultUpsertBatchRequest,
  RaceUpsertBatchRequest,
  ScrapeScheduleStatus,
  ScrapeScheduleUpdateRequest,
  ScrapeSyncRequest,
  ScrapeSyncResponse,
  ScrapeSyncScheduleRequest,
  ScrapeSyncStatus,
  SnapshotKind,
  TokenResponse,
  UserRegisterRequest,
  VenueListResponse,
} from "./generated";
import { apiFetch, UnauthorizedHandler } from "./http";

export type ApiCtx = {
  baseUrl: string;
  token?: string | null;
  onUnauthorized?: UnauthorizedHandler;
};

export const api = {
  health: (ctx: ApiCtx) => apiFetch<HealthResponse>({ ...ctx, path: "/health", method: "GET" }),

  login: (ctx: Omit<ApiCtx, "token" | "onUnauthorized">, req: PasswordLoginRequest) =>
    apiFetch<TokenResponse>({
      ...ctx,
      path: "/auth/login",
      method: "POST",
      body: req,
      retryOnUnauthorized: false,
    }),

  register: (ctx: Omit<ApiCtx, "token" | "onUnauthorized">, req: UserRegisterRequest) =>
    apiFetch<TokenResponse>({
      ...ctx,
      path: "/auth/register",
      method: "POST",
      body: req,
      retryOnUnauthorized: false,
    }),

  refresh: (ctx: Omit<ApiCtx, "token" | "onUnauthorized">) =>
    apiFetch<TokenResponse>({ ...ctx, path: "/auth/refresh", method: "POST", retryOnUnauthorized: false }),

  logout: (ctx: Omit<ApiCtx, "token" | "onUnauthorized">) =>
    apiFetch<void>({ ...ctx, path: "/auth/logout", method: "POST", retryOnUnauthorized: false }),

  clientCredentialsToken: (ctx: Omit<ApiCtx, "token" | "onUnauthorized">, req: ClientCredentialsTokenRequest) =>
    apiFetch<TokenResponse>({ ...ctx, path: "/auth/token", method: "POST", body: req, retryOnUnauthorized: false }),

  listOAuthClients: (ctx: ApiCtx) =>
    apiFetch<OAuthClientListResponse>({ ...ctx, path: "/admin/oauth-clients", method: "GET" }),

  createOAuthClient: (ctx: ApiCtx, req: OAuthClientCreateRequest) =>
    apiFetch<OAuthClientCreateResponse>({ ...ctx, path: "/admin/oauth-clients", method: "POST", body: req }),

  updateOAuthClient: (ctx: ApiCtx, clientId: string, req: OAuthClientUpdateRequest) =>
    apiFetch<OAuthClientView>({
      ...ctx,
      path: `/admin/oauth-clients/${encodeURIComponent(clientId)}`,
      method: "PATCH",
      body: req,
    }),

  revokeOAuthClient: (ctx: ApiCtx, clientId: string) =>
    apiFetch<void>({
      ...ctx,
      path: `/admin/oauth-clients/${encodeURIComponent(clientId)}`,
      method: "DELETE",
    }),

  rotateOAuthClientSecret: (ctx: ApiCtx, clientId: string) =>
    apiFetch<OAuthClientRotateSecretResponse>({
      ...ctx,
      path: `/admin/oauth-clients/${encodeURIComponent(clientId)}/rotate-secret`,
      method: "POST",
    }),

  listVenues: (ctx: ApiCtx) => apiFetch<VenueListResponse>({ ...ctx, path: "/venues", method: "GET" }),

  listRaces: (ctx: ApiCtx, query: { race_date: string; baba_code?: number; page?: number; page_size?: number }) =>
    apiFetch<RaceListResponse>({ ...ctx, path: "/races", method: "GET", query }),

  getRace: (ctx: ApiCtx, raceId: number) => apiFetch<Race>({ ...ctx, path: `/races/${raceId}`, method: "GET" }),

  listRaceEntries: (ctx: ApiCtx, raceId: number) =>
    apiFetch<RaceEntryListResponse>({ ...ctx, path: `/races/${raceId}/entries`, method: "GET" }),

  getRaceOdds: (
    ctx: ApiCtx,
    raceId: number,
    query: { snapshot_kind: SnapshotKind; bet_type: BetType; odds_flg?: number | null },
  ) => apiFetch<OddsSnapshotQueryResponse>({ ...ctx, path: `/races/${raceId}/odds`, method: "GET", query }),

  listRaceResults: (ctx: ApiCtx, raceId: number) =>
    apiFetch<RaceResultListResponse>({ ...ctx, path: `/races/${raceId}/results`, method: "GET" }),

  listRacePayouts: (ctx: ApiCtx, raceId: number) =>
    apiFetch<PayoutListResponse>({ ...ctx, path: `/races/${raceId}/payouts`, method: "GET" }),

  scrapeRacesUpsert: (ctx: ApiCtx, req: RaceUpsertBatchRequest) =>
    apiFetch<BatchUpsertResponse>({ ...ctx, path: "/scrape/races", method: "POST", body: req }),

  scrapeRaceEntriesUpsert: (ctx: ApiCtx, req: RaceEntryUpsertBatchRequest) =>
    apiFetch<BatchUpsertResponse>({ ...ctx, path: "/scrape/race-entries", method: "POST", body: req }),

  scrapeOddsSnapshotsUpsert: (ctx: ApiCtx, req: OddsSnapshotUpsertRequest) =>
    apiFetch<OddsSnapshotUpsertResponse>({ ...ctx, path: "/scrape/odds-snapshots", method: "POST", body: req }),

  scrapeRaceResultsUpsert: (ctx: ApiCtx, req: RaceResultUpsertBatchRequest) =>
    apiFetch<BatchUpsertResponse>({ ...ctx, path: "/scrape/race-results", method: "POST", body: req }),

  scrapePayoutsUpsert: (ctx: ApiCtx, req: PayoutUpsertBatchRequest) =>
    apiFetch<BatchUpsertResponse>({ ...ctx, path: "/scrape/payouts", method: "POST", body: req }),

  scrapeRaceChangesInsert: (ctx: ApiCtx, req: RaceChangeInsertBatchRequest) =>
    apiFetch<BatchUpsertResponse>({ ...ctx, path: "/scrape/race-changes", method: "POST", body: req }),

  scrapeScheduleStatus: (ctx: ApiCtx) =>
    apiFetch<ScrapeScheduleStatus>({ ...ctx, path: "/scrape/schedule", method: "GET" }),

  scrapeScheduleUpdate: (ctx: ApiCtx, req: ScrapeScheduleUpdateRequest) =>
    apiFetch<ScrapeScheduleStatus>({ ...ctx, path: "/scrape/schedule", method: "POST", body: req }),

  scrapeManualTasksRequest: (ctx: ApiCtx, req: ManualScrapeTaskRequest) =>
    apiFetch<ManualScrapeTaskResponse>({ ...ctx, path: "/scrape/manual-tasks", method: "POST", body: req }),

  scrapeSyncStatus: (ctx: ApiCtx) =>
    apiFetch<ScrapeSyncStatus>({ ...ctx, path: "/scrape/sync/status", method: "GET" }),

  scrapeSyncScheduleUpdate: (ctx: ApiCtx, req: ScrapeSyncScheduleRequest) =>
    apiFetch<ScrapeSyncStatus>({ ...ctx, path: "/scrape/sync/schedule", method: "POST", body: req }),

  scrapeSyncTrigger: (ctx: ApiCtx, req?: ScrapeSyncRequest) =>
    apiFetch<ScrapeSyncResponse>({
      ...ctx,
      path: "/scrape/sync",
      method: "POST",
      body: req ?? {},
    }),
};
