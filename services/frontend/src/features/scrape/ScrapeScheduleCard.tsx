import React from "react";

import { ScrapeScheduleStatus, ScrapeScheduleUpdateRequest } from "@/api/generated";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

type Props = {
  status?: ScrapeScheduleStatus;
  isLoading: boolean;
  loadError?: unknown;
  saveError?: unknown;
  saving?: boolean;
  onSave: (payload: ScrapeScheduleUpdateRequest) => void;
  onRefresh: () => void;
};

function formatCodes(codes?: number[] | null): string {
  if (!codes || codes.length === 0) return "";
  return codes.join(", ");
}

function parseCodes(input: string): { codes: number[]; error?: string } {
  const trimmed = input.trim();
  if (!trimmed) return { codes: [] };
  const tokens = trimmed.split(/[,\s]+/).filter(Boolean);
  const codes = tokens.map((tok) => Number(tok));
  if (codes.some((code) => !Number.isFinite(code))) {
    return { codes: [], error: "baba_codes は数値のみで指定してください。" };
  }
  return { codes: codes.map((code) => Math.trunc(code)) };
}

function formatDate(value?: string | null): string {
  return value || "-";
}

export function ScrapeScheduleCard({
  status,
  isLoading,
  loadError,
  saveError,
  saving,
  onSave,
  onRefresh,
}: Props): React.JSX.Element {
  const [enabled, setEnabled] = React.useState(false);
  const [babaCodesText, setBabaCodesText] = React.useState("");
  const [inputError, setInputError] = React.useState<string | null>(null);

  const codesValue = status?.baba_codes?.join(",") ?? "";
  React.useEffect(() => {
    if (status) {
      setEnabled(status.enabled);
      setBabaCodesText(formatCodes(status.baba_codes));
      setInputError(null);
    }
  }, [status?.enabled, codesValue]);

  const handleSave = () => {
    const { codes, error } = parseCodes(babaCodesText);
    if (error) {
      setInputError(error);
      return;
    }
    setInputError(null);
    onSave({ enabled, baba_codes: codes });
  };

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="cardHeader">
        <h2 className="cardTitle">Scrape Schedule</h2>
        <span className={enabled ? "pill ok" : "pill"}>{enabled ? "ENABLED" : "DISABLED"}</span>
      </div>

      {isLoading ? <Loading label="Loading scrape schedule..." /> : null}
      {loadError ? <ErrorBox error={loadError} /> : null}
      {saveError ? <ErrorBox error={saveError} /> : null}

      {status ? (
        <div className="small" style={{ marginBottom: 10 }}>
          updated_at: {formatDate(status.updated_at)}
        </div>
      ) : null}

      <div className="row">
        <label>
          <div className="small">enabled</div>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        </label>

        <label>
          <div className="small">baba_codes</div>
          <input
            className="input"
            placeholder="1, 2, 3"
            value={babaCodesText}
            onChange={(e) => setBabaCodesText(e.target.value)}
          />
        </label>

        <button className="btn" onClick={onRefresh}>
          Refresh
        </button>

        <button className="btn" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>

      {inputError ? <div className="small">{inputError}</div> : null}
    </div>
  );
}
