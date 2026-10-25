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
      <h1 className="pageTitle">設定</h1>
      <p className="pageDesc">認証情報とAPIの接続先を確認・設定します。</p>

      <div className="grid2">
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">API接続先</h2>
          </div>
          <div className="small">接続先URL</div>
          <div style={{ marginTop: 6, fontFamily: "ui-monospace, monospace" }}>{baseUrl}</div>

          <div className="small" style={{ marginTop: 12 }}>
            接続先の変更は、管理者がビルド時の環境変数 VITE_API_BASE_URL で行います。
          </div>
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">ログイン状態</h2>
          </div>

          <div className="row" style={{ justifyContent: "space-between" }}>
            <div className="small">ユーザー認証トークン</div>
            <div className="pill">{auth.userToken ? "設定済み" : "未設定"}</div>
          </div>

          <div className="row" style={{ marginTop: 12, justifyContent: "flex-end" }}>
            <button className="btn danger" onClick={() => auth.logout()} disabled={!auth.userToken}>
              ログアウト
            </button>
          </div>

          <div className="small" style={{ marginTop: 10 }}>
            ログイン情報を削除してログアウトします。
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="cardHeader">
          <h2 className="cardTitle">外部連携用トークン</h2>
          <div className="row">
            <label className="small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={auth.useServiceToken}
                onChange={(e) => auth.setUseServiceToken(e.target.checked)}
              />
              外部連携用トークンを使用する
            </label>
          </div>
        </div>

        <div className="small">外部連携用トークン（このブラウザーに保存されます）</div>
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
            保存
          </button>

          <button
            className="btn danger"
            onClick={() => {
              setServiceTokenDraft("");
              auth.setServiceToken(null);
              auth.setUseServiceToken(false);
            }}
          >
            クリア
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          外部連携用トークンは「外部連携」画面で発行できます。データ登録時の認証に使用します。
        </div>
      </div>
    </div>
  );
}
