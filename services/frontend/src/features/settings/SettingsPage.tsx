import React from "react";

import { getApiBaseUrl } from "@/api/http";
import { useAuth } from "@/app/auth/useAuth";

export function SettingsPage(): React.JSX.Element {
  const auth = useAuth();
  const baseUrl = getApiBaseUrl();

  const [serviceTokenDraft, setServiceTokenDraft] = React.useState(auth.serviceToken || "");

  React.useEffect(() => {
    setServiceTokenDraft(auth.serviceToken || "");
  }, [auth.serviceToken]);

  return (
    <div>
      <h1 className="pageTitle">Settings</h1>
      <p className="pageDesc">トークンや API base URL を確認します。</p>

      <div className="grid2">
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">API</h2>
          </div>
          <div className="small">VITE_API_BASE_URL</div>
          <div style={{ marginTop: 6, fontFamily: "ui-monospace, monospace" }}>{baseUrl}</div>

          <div className="small" style={{ marginTop: 12 }}>
            docker-compose.yml の環境変数 VITE_API_BASE_URL を変更することで切り替えできます。
          </div>
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">User session</h2>
          </div>

          <div className="row" style={{ justifyContent: "space-between" }}>
            <div className="small">userToken</div>
            <div className="pill">{auth.userToken ? "SET" : "NONE"}</div>
          </div>

          <div className="row" style={{ marginTop: 12, justifyContent: "flex-end" }}>
            <button className="btn danger" onClick={() => auth.logout()} disabled={!auth.userToken}>
              Logout (clear user token)
            </button>
          </div>

          <div className="small" style={{ marginTop: 10 }}>
            /auth/logout を呼び出し、userToken を削除します。
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="cardHeader">
          <h2 className="cardTitle">Service token</h2>
          <div className="row">
            <label className="small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={auth.useServiceToken}
                onChange={(e) => auth.setUseServiceToken(e.target.checked)}
              />
              Use service token
            </label>
          </div>
        </div>

        <div className="small">Bearer access token (保存されます)</div>
        <textarea
          className="textarea"
          value={serviceTokenDraft}
          onChange={(e) => setServiceTokenDraft(e.target.value)}
          style={{ minHeight: 160 }}
        />

        <div className="row" style={{ marginTop: 10, justifyContent: "space-between" }}>
          <button
            className="btn"
            onClick={() => {
              auth.setServiceToken(serviceTokenDraft.trim() || null);
            }}
          >
            Save
          </button>

          <button
            className="btn danger"
            onClick={() => {
              setServiceTokenDraft("");
              auth.setServiceToken(null);
              auth.setUseServiceToken(false);
            }}
          >
            Clear
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          Service token は /auth/token（client_credentials）で発行し、/scrape/* の呼び出しに利用します。
        </div>
      </div>
    </div>
  );
}
