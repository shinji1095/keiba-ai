import React from "react";

export function Loading({ label }: { label?: string }): React.JSX.Element {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="small">{label || "Loading..."}</div>
        <div className="pill">…</div>
      </div>
    </div>
  );
}
