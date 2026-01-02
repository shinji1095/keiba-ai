import React from "react";

import { ManualScrapeTaskRequest, ManualScrapeTaskResponse } from "@/api/generated";
import { ErrorBox } from "@/shared/ui/ErrorBox";

type Props = {
  response?: ManualScrapeTaskResponse;
  requestError?: unknown;
  requesting?: boolean;
  onRequest: (payload: ManualScrapeTaskRequest) => void;
  onClear?: () => void;
};

function formatDate(value?: string | null): string {
  return value || "-";
}

function parseOptionalInt(s: string): number | null {
  const trimmed = s.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

export function ManualScrapeTaskCard({
  response,
  requestError,
  requesting,
  onRequest,
  onClear,
}: Props): React.JSX.Element {
  const [babaCodeText, setBabaCodeText] = React.useState("");
  const [raceDate, setRaceDate] = React.useState("");
  const [raceNoText, setRaceNoText] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [inputError, setInputError] = React.useState<string | null>(null);

  const handleRequest = () => {
    const babaCode = parseOptionalInt(babaCodeText);
    if (babaCode === null) {
      setInputError("baba_code は必須です（数値）。");
      return;
    }

    const raceNo = parseOptionalInt(raceNoText);
    if (raceNo !== null && (raceNo < 1 || raceNo > 12)) {
      setInputError("race_no は 1〜12 で指定してください。");
      return;
    }

    const payload: ManualScrapeTaskRequest = {
      baba_code: babaCode,
      ...(raceDate.trim() ? { race_date: raceDate.trim() } : {}),
      ...(raceNo !== null ? { race_no: raceNo } : {}),
      ...(reason.trim() ? { reason: reason.trim() } : {}),
    };
    setInputError(null);
    onRequest(payload);
  };

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="cardHeader">
        <h2 className="cardTitle">Manual Scrape Task</h2>
        <span className={response ? "pill ok" : "pill"}>{response ? response.status.toUpperCase() : "IDLE"}</span>
      </div>

      {requestError ? <ErrorBox error={requestError} /> : null}

      <div className="row">
        <label>
          <div className="small">baba_code (required)</div>
          <input
            className="input"
            inputMode="numeric"
            placeholder="18"
            value={babaCodeText}
            onChange={(e) => setBabaCodeText(e.target.value)}
          />
        </label>

        <label>
          <div className="small">race_date (optional)</div>
          <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
        </label>

        <label>
          <div className="small">race_no (optional)</div>
          <input
            className="input"
            inputMode="numeric"
            placeholder="1"
            value={raceNoText}
            onChange={(e) => setRaceNoText(e.target.value)}
          />
        </label>
      </div>

      <div className="row" style={{ marginTop: 10, alignItems: "stretch" }}>
        <label style={{ width: "100%" }}>
          <div className="small">reason (optional)</div>
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="manual" />
        </label>

        <button className="btn primary" onClick={handleRequest} disabled={requesting}>
          {requesting ? "Requesting..." : "Request"}
        </button>

        {onClear ? (
          <button className="btn" onClick={onClear} disabled={requesting && !response}>
            Clear
          </button>
        ) : null}
      </div>

      {inputError ? <div className="small" style={{ marginTop: 8 }}>{inputError}</div> : null}

      {response ? (
        <div className="small" style={{ marginTop: 10 }}>
          task_id: <span style={{ fontFamily: "ui-monospace, monospace" }}>{response.task_id}</span>
          <br />
          accepted_at: {formatDate(response.accepted_at)}
        </div>
      ) : null}
    </div>
  );
}


