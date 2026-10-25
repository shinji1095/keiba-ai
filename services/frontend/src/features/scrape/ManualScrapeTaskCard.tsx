import React from "react";
import { statusLabel } from "@/shared/labels";

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
      setInputError("競馬場コードを数値で入力してください。");
      return;
    }

    const raceNo = parseOptionalInt(raceNoText);
    if (raceNo !== null && (raceNo < 1 || raceNo > 12)) {
      setInputError("レース番号は1〜12で指定してください。");
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
        <h2 className="cardTitle">手動収集</h2>
        <span className={response ? "pill ok" : "pill"}>{response ? statusLabel(response.status) : "待機中"}</span>
      </div>

      {requestError ? <ErrorBox error={requestError} /> : null}

      <div className="row">
        <label>
          <div className="small">競馬場コード（必須）</div>
          <input
            className="input"
            inputMode="numeric"
            placeholder="18"
            value={babaCodeText}
            onChange={(e) => setBabaCodeText(e.target.value)}
          />
        </label>

        <label>
          <div className="small">開催日（任意）</div>
          <input className="input" type="date" value={raceDate} onChange={(e) => setRaceDate(e.target.value)} />
        </label>

        <label>
          <div className="small">レース番号（任意）</div>
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
          <div className="small">依頼理由（任意）</div>
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="例：取得漏れの再収集" />
        </label>

        <button className="btn primary" onClick={handleRequest} disabled={requesting}>
          {requesting ? "依頼中…" : "収集を依頼"}
        </button>

        {onClear ? (
          <button className="btn" onClick={onClear} disabled={requesting && !response}>
            クリア
          </button>
        ) : null}
      </div>

      {inputError ? <div className="small" style={{ marginTop: 8 }}>{inputError}</div> : null}

      {response ? (
        <div className="small" style={{ marginTop: 10 }}>
          収集依頼ID： <span style={{ fontFamily: "ui-monospace, monospace" }}>{response.task_id}</span>
          <br />
          受付日時： {formatDate(response.accepted_at)}
        </div>
      ) : null}
    </div>
  );
}


