import React from "react";

import { ScrapeScheduleStatus, ScrapeScheduleUpdateRequest } from "@/api/generated";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

const SNAPSHOT_KIND_OPTIONS = [
  { value: "final", label: "final (発走直前)" },
  { value: "t_minus_1m", label: "t_minus_1m (発走1分前)" },
  { value: "t_minus_5m", label: "t_minus_5m (発走5分前)" },
  { value: "t_minus_10m", label: "t_minus_10m (発走10分前)" },
  { value: "t_minus_20m", label: "t_minus_20m (発走20分前)" },
  { value: "t_minus_30m", label: "t_minus_30m (発走30分前)" },
  { value: "t_minus_60m", label: "t_minus_60m (発走60分前)" },
] as const;

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

function normalizeSnapshotKinds(input?: string[] | null): string[] {
  const allowed = new Set<string>(SNAPSHOT_KIND_OPTIONS.map((o) => o.value));
  const selected = new Set((input ?? []).filter((k) => allowed.has(k)));
  if (selected.size === 0) selected.add("final");
  return SNAPSHOT_KIND_OPTIONS.map((o) => o.value).filter((k) => selected.has(k));
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
  const [snapshotKinds, setSnapshotKinds] = React.useState<string[]>(["final"]);

  const codesValue = status?.baba_codes?.join(",") ?? "";
  React.useEffect(() => {
    if (status) {
      setEnabled(status.enabled);
      setBabaCodesText(formatCodes(status.baba_codes));
      setSnapshotKinds(normalizeSnapshotKinds(status.snapshot_kinds));
      setInputError(null);
    }
  }, [status?.enabled, codesValue, status?.snapshot_kinds?.join(",")]);

  const toggleSnapshotKind = (kind: string, checked: boolean) => {
    const next = new Set(snapshotKinds);
    if (checked) next.add(kind);
    else next.delete(kind);
    setSnapshotKinds(normalizeSnapshotKinds([...next]));
  };

  const handleSave = () => {
    const { codes, error } = parseCodes(babaCodesText);
    if (error) {
      setInputError(error);
      return;
    }
    setInputError(null);
    onSave({ enabled, baba_codes: codes, snapshot_kinds: snapshotKinds });
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

        <div>
          <div className="small" style={{ marginBottom: 6 }}>
            snapshot_kinds（複数選択可）
          </div>
          <div className="small" style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {SNAPSHOT_KIND_OPTIONS.map((opt) => (
              <label key={opt.value} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <input
                  type="checkbox"
                  checked={snapshotKinds.includes(opt.value)}
                  onChange={(e) => toggleSnapshotKind(opt.value, e.target.checked)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

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
