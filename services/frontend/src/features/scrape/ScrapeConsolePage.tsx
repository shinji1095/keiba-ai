import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { JsonView } from "@/shared/ui/JsonView";
import { ScrapeScheduleCard } from "./ScrapeScheduleCard";
import { SyncControlCard } from "./SyncControlCard";
import { ManualScrapeTaskCard } from "./ManualScrapeTaskCard";

type ScrapeOpKey =
  | "races"
  | "race-entries"
  | "odds-snapshots"
  | "race-results"
  | "payouts"
  | "race-changes";

type OpDef = {
  label: string;
  template: unknown;
  run: (ctx: ReturnType<typeof useApiCtx>, body: any) => Promise<unknown>;
};

const templates: Record<ScrapeOpKey, unknown> = {
  races: {
    items: [
      {
        race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
        race_name: "Sample Race",
        start_time: "12:00",
        status: "scheduled",
      },
    ],
  },
  "race-entries": {
    items: [
      {
        race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
        horse_number: 1,
        horse_name: "Sample Horse",
        post_position: 1,
      },
    ],
  },
  "odds-snapshots": {
    snapshot: {
      race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
      snapshot_kind: "final",
      bet_type: "tansho",
      captured_at: "2025-01-01T12:00:00Z",
      source: "netkeiba",
    },
    items: [
      {
        legs: [1],
        is_ordered: false,
        odds_min: 2.3,
        odds_max: null,
        popularity: 1,
      },
    ],
  },
  "race-results": {
    items: [
      {
        race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
        horse_number: 1,
        rank: 1,
        finish_time: "1:34.5",
      },
    ],
  },
  payouts: {
    items: [
      {
        race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
        bet_type: "tansho",
        legs: [1],
        payout_yen: 230,
        popularity: 1,
      },
    ],
  },
  "race-changes": {
    items: [
      {
        race_key: { race_date: "2025-01-01", baba_code: 1, race_no: 1 },
        changed_at: "2025-01-01T10:00:00Z",
        change_kind: "status",
        before: "scheduled",
        after: "closed",
      },
    ],
  },
};

const ops: Record<ScrapeOpKey, Omit<OpDef, "run">> = {
  races: { label: "POST /scrape/races", template: templates.races },
  "race-entries": { label: "POST /scrape/race-entries", template: templates["race-entries"] },
  "odds-snapshots": { label: "POST /scrape/odds-snapshots", template: templates["odds-snapshots"] },
  "race-results": { label: "POST /scrape/race-results", template: templates["race-results"] },
  payouts: { label: "POST /scrape/payouts", template: templates.payouts },
  "race-changes": { label: "POST /scrape/race-changes", template: templates["race-changes"] },
};

function pretty(x: unknown): string {
  return JSON.stringify(x, null, 2);
}

export function ScrapeConsolePage(): React.JSX.Element {
  const ctx = useApiCtx();
  const auth = useAuth();
  const qc = useQueryClient();

  const qSyncStatus = useQuery({
    queryKey: ["sync-status"],
    queryFn: () => api.scrapeSyncStatus(ctx),
  });

  const qScrapeSchedule = useQuery({
    queryKey: ["scrape-schedule"],
    queryFn: () => api.scrapeScheduleStatus(ctx),
  });

  const scrapeScheduleMutation = useMutation({
    mutationFn: (payload: Parameters<typeof api.scrapeScheduleUpdate>[1]) =>
      api.scrapeScheduleUpdate(ctx, payload),
    onSuccess: (data) => {
      qc.setQueryData(["scrape-schedule"], data);
    },
  });

  const syncScheduleMutation = useMutation({
    mutationFn: (payload: Parameters<typeof api.scrapeSyncScheduleUpdate>[1]) =>
      api.scrapeSyncScheduleUpdate(ctx, payload),
    onSuccess: (data) => {
      qc.setQueryData(["sync-status"], data);
    },
  });

  const syncTriggerMutation = useMutation({
    mutationFn: () => api.scrapeSyncTrigger(ctx, { reason: "manual" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sync-status"] });
    },
  });

  const manualTaskMutation = useMutation({
    mutationFn: (payload: Parameters<typeof api.scrapeManualTasksRequest>[1]) => api.scrapeManualTasksRequest(ctx, payload),
  });

  const [op, setOp] = React.useState<ScrapeOpKey>("odds-snapshots");
  const [jsonText, setJsonText] = React.useState(pretty(templates["odds-snapshots"]));

  React.useEffect(() => {
    setJsonText(pretty(templates[op]));
  }, [op]);

  const runMutation = useMutation({
    mutationFn: async (): Promise<unknown> => {
      const body = JSON.parse(jsonText);
      switch (op) {
        case "races":
          return await api.scrapeRacesUpsert(ctx, body);
        case "race-entries":
          return await api.scrapeRaceEntriesUpsert(ctx, body);
        case "odds-snapshots":
          return await api.scrapeOddsSnapshotsUpsert(ctx, body);
        case "race-results":
          return await api.scrapeRaceResultsUpsert(ctx, body);
        case "payouts":
          return await api.scrapePayoutsUpsert(ctx, body);
        case "race-changes":
          return await api.scrapeRaceChangesInsert(ctx, body);
      }
    },
  });

  return (
    <div>
      <h1 className="pageTitle">Scrape Console</h1>
      <p className="pageDesc">
        /scrape/* 系エンドポイントを手動で呼び出します。token mode が Service の場合は serviceToken を使用します。
      </p>

      {!auth.activeToken ? <div className="alert">Token is not set.</div> : null}

      <ScrapeScheduleCard
        status={qScrapeSchedule.data}
        isLoading={qScrapeSchedule.isLoading}
        loadError={qScrapeSchedule.error}
        saveError={scrapeScheduleMutation.error}
        saving={scrapeScheduleMutation.isPending}
        onSave={(payload) => scrapeScheduleMutation.mutate(payload)}
        onRefresh={() => qScrapeSchedule.refetch()}
      />

      <SyncControlCard
        status={qSyncStatus.data}
        isLoading={qSyncStatus.isLoading}
        loadError={qSyncStatus.error}
        saveError={syncScheduleMutation.error}
        triggerError={syncTriggerMutation.error}
        saving={syncScheduleMutation.isPending}
        triggering={syncTriggerMutation.isPending}
        onSave={(payload) => syncScheduleMutation.mutate(payload)}
        onTrigger={() => syncTriggerMutation.mutate()}
        onRefresh={() => qSyncStatus.refetch()}
      />

      <ManualScrapeTaskCard
        response={manualTaskMutation.data}
        requestError={manualTaskMutation.error}
        requesting={manualTaskMutation.isPending}
        onRequest={(payload) => manualTaskMutation.mutate(payload)}
        onClear={() => manualTaskMutation.reset()}
      />

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row">
          <label>
            <div className="small">operation</div>
            <select className="select" value={op} onChange={(e) => setOp(e.target.value as ScrapeOpKey)}>
              {Object.entries(ops).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>

          <div className="pill">{auth.useServiceToken ? "Service token" : "User token"}</div>

          <a className="btn" href="/settings">
            Settings
          </a>

          <button className="btn primary" onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            {runMutation.isPending ? "Running..." : "Run"}
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          Request body (JSON)
        </div>
        <textarea className="textarea" value={jsonText} onChange={(e) => setJsonText(e.target.value)} />
      </div>

      {runMutation.error ? <ErrorBox error={runMutation.error} /> : null}

      {runMutation.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Response</h2>
          </div>
          <JsonView value={runMutation.data} />
        </div>
      ) : null}
    </div>
  );
}
