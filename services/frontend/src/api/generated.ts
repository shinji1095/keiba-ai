/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Auto-generated TypeScript types from docs/21_openapi.yaml.
 *
 * If you update the OpenAPI spec, regenerate this file accordingly.
 * (This repository includes the spec under docs/21_openapi.yaml.)
 */
export interface ErrorEnvelope {
  "error": {
  "code": string;
  "message": string;
  "details"?: Record<string, unknown>;
};
}

export interface HealthResponse {
  "status": string;
}

export interface PasswordLoginRequest {
  "username": string;
  "password": string;
}

export interface UserRegisterRequest {
  "username": string;
  "password": string;
}

export interface ClientCredentialsTokenRequest {
  "grant_type": "client_credentials";
  "client_id": string;
  "client_secret": string;
  /**
   * Space separated scopes (optional)
   */
  "scope"?: string | null;
}

export interface TokenResponse {
  /**
   * JWT access token
   */
  "access_token": string;
  "token_type": "Bearer";
  /**
   * seconds
   */
  "expires_in": number;
  "issued_at"?: string | null;
}

export interface RaceKey {
  "race_date": string;
  /**
   * 競馬場コード
   */
  "baba_code": number;
  "race_no": number;
}

export type BetType = "tansho" | "fukusho" | "wakuren" | "wakutan" | "umaren" | "umatan" | "wide" | "sanrenpuku" | "sanrentan";

export type SnapshotKind = string;

export interface ScrapeScheduleStatus {
  "enabled": boolean;
  "baba_codes"?: number[] | null;
  "mode"?: string | null;
  "updated_at": string;
  "note"?: string | null;
}

export interface ScrapeScheduleUpdateRequest {
  "enabled": boolean;
  "baba_codes"?: number[] | null;
}

export interface ManualScrapeTaskRequest {
  "race_date"?: string | null;
  /**
   * 競馬場コード
   */
  "baba_code": number;
  "race_no"?: number | null;
  "reason"?: string | null;
}

export interface ManualScrapeTaskResponse {
  "task_id": string;
  "status": string;
  "accepted_at": string;
}

export interface ScrapeSyncRequest {
  "reason"?: string | null;
}

export interface ScrapeSyncScheduleRequest {
  "enabled": boolean;
  "interval_days": number;
  "diff_enabled"?: boolean | null;
}

export interface ScrapeSyncResponse {
  "sync_id": string;
  "status": string;
  "started_at": string;
}

export interface ScrapeSyncStatus {
  "enabled": boolean;
  "interval_days": number;
  "diff_enabled": boolean;
  "last_synced_at"?: string | null;
  "next_scheduled_at"?: string | null;
  "last_fingerprint"?: string | null;
  "last_attempted_at"?: string | null;
  "last_status"?: string | null;
  "last_error"?: string | null;
  "last_trigger"?: string | null;
  "schedule_updated_at"?: string | null;
}

export interface OAuthClientCreateRequest {
  "name": string;
  "scopes": string[];
  "is_active"?: boolean;
}

export interface OAuthClientCreateResponse {
  "client": OAuthClientWithSecret;
}

export interface OAuthClientRotateSecretResponse {
  "client": OAuthClientWithSecret;
}

export interface OAuthClientUpdateRequest {
  "scopes"?: string[] | null;
  "is_active"?: boolean | null;
}

export interface OAuthClientListResponse {
  "items": OAuthClientView[];
  "page": number;
  "page_size": number;
}

export interface OAuthClientView {
  "client_id": string;
  "name": string;
  "scopes": string[];
  "is_active": boolean;
  "created_at": string;
  "revoked_at"?: string | null;
}

export type OAuthClientWithSecret = OAuthClientView & {
  "client_secret": string;
};

export interface Venue {
  "baba_code": number;
  "venue_name": string;
}

export interface VenueListResponse {
  "items": Venue[];
}

export interface Race {
  "race_id": number;
  "race_key": RaceKey;
  "start_time"?: string | null;
  "distance_m"?: number | null;
  "course"?: string | null;
  "weather"?: string | null;
  "track_condition"?: string | null;
  "race_name"?: string | null;
  "field_size"?: number | null;
  "status"?: string | null;
}

export interface RaceSummary {
  "race_id": number;
  "race_key": RaceKey;
  "start_time"?: string | null;
  "race_name"?: string | null;
  "status"?: string | null;
}

export interface RaceListResponse {
  "items": RaceSummary[];
  "page": number;
  "page_size": number;
}

export interface RaceEntry {
  "race_entry_id": number;
  "race_id": number;
  "horse_id"?: number | null;
  "post_position"?: number | null;
  "horse_number": number;
  "horse_name": string;
  "jockey_name"?: string | null;
  "trainer_name"?: string | null;
  "handicap_kg"?: number | null;
  "body_weight"?: number | null;
  "body_weight_diff"?: number | null;
}

export interface RaceEntryListResponse {
  "items": RaceEntry[];
}

export interface RaceChange {
  "race_change_id": number;
  "race_id": number;
  "change_type": string;
  "payload": Record<string, unknown>;
  "captured_at": string;
}

export interface OddsSnapshot {
  "odds_snapshot_id": number;
  "race_id": number;
  "bet_type": BetType;
  "snapshot_kind": SnapshotKind;
  "captured_at": string;
  "source_url": string;
  "odds_flg"?: number | null;
  "is_final": boolean;
}

export interface OddsItem {
  "odds_item_id": number;
  "odds_snapshot_id": number;
  /**
   * 組合せ（例: [3], [3,7], [3,7,12]）
   */
  "legs": number[];
  "is_ordered": boolean;
  "odds_min": number | null;
  "odds_max"?: number | null;
  "popularity"?: number | null;
  "raw_text"?: string | null;
}

export interface OddsSnapshotQueryResponse {
  "snapshot": OddsSnapshot;
  "items": OddsItem[];
}

export interface RaceResult {
  "race_result_id": number;
  "race_id": number;
  "finish_position": number;
  "horse_number"?: number | null;
  "time_str"?: string | null;
  "margin"?: string | null;
  "last3f"?: number | null;
  "popularity"?: number | null;
  "corner1"?: string | null;
  "corner2"?: string | null;
  "corner3"?: string | null;
  "corner4"?: string | null;
}

export interface RaceResultListResponse {
  "items": RaceResult[];
}

export interface Payout {
  "payout_id": number;
  "race_id": number;
  "bet_type": BetType;
  "legs": number[];
  "is_ordered": boolean;
  "payout_yen": number | null;
  "popularity"?: number | null;
}

export interface PayoutListResponse {
  "items": Payout[];
}

export interface BatchUpsertResponse {
  "accepted": number;
  "upserted": number;
  "warnings"?: string[] | null;
}

export interface RaceUpsert {
  "race_key": RaceKey;
  "start_time"?: string | null;
  "distance_m"?: number | null;
  "course"?: string | null;
  "weather"?: string | null;
  "track_condition"?: string | null;
  "race_name"?: string | null;
  "field_size"?: number | null;
  "status"?: string | null;
}

export interface RaceUpsertBatchRequest {
  "items": RaceUpsert[];
}

export interface RaceEntryUpsert {
  "race_key": RaceKey;
  "horse_id"?: number | null;
  "post_position"?: number | null;
  "horse_number": number;
  "horse_name": string;
  "jockey_name"?: string | null;
  "trainer_name"?: string | null;
  "handicap_kg"?: number | null;
  "body_weight"?: number | null;
  "body_weight_diff"?: number | null;
}

export interface RaceEntryUpsertBatchRequest {
  "items": RaceEntryUpsert[];
}

export interface OddsItemUpsert {
  "legs": number[];
  "is_ordered": boolean;
  "odds_min"?: number | null;
  "odds_max"?: number | null;
  "popularity"?: number | null;
  "raw_text"?: string | null;
}

export interface OddsSnapshotUpsertRequest {
  "race_key": RaceKey;
  "bet_type": BetType;
  "snapshot_kind": SnapshotKind;
  "captured_at": string;
  "source_url": string;
  "odds_flg"?: number | null;
  "is_final"?: boolean;
  "items": OddsItemUpsert[];
}

export interface OddsSnapshotUpsertResponse {
  "race_id": number;
  "bet_type": BetType;
  "snapshot_kind": SnapshotKind;
  "odds_snapshot_id": number;
  "num_items": number;
}

export interface RaceResultUpsert {
  "race_key": RaceKey;
  "finish_position": number;
  "horse_number"?: number | null;
  "time_str"?: string | null;
  "margin"?: string | null;
  "last3f"?: number | null;
  "popularity"?: number | null;
  "corner1"?: string | null;
  "corner2"?: string | null;
  "corner3"?: string | null;
  "corner4"?: string | null;
}

export interface RaceResultUpsertBatchRequest {
  "items": RaceResultUpsert[];
}

export interface PayoutUpsert {
  "race_key": RaceKey;
  "bet_type": BetType;
  "legs": number[];
  "is_ordered": boolean;
  "payout_yen"?: number | null;
  "popularity"?: number | null;
}

export interface PayoutUpsertBatchRequest {
  "items": PayoutUpsert[];
}

export interface RaceChangeInsert {
  "race_key": RaceKey;
  "change_type": string;
  "payload": Record<string, unknown>;
  "captured_at": string;
}

export interface RaceChangeInsertBatchRequest {
  "items": RaceChangeInsert[];
}
