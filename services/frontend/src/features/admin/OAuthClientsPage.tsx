import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { OAuthClientWithSecret, TokenResponse } from "@/api/generated";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";
import { JsonView } from "@/shared/ui/JsonView";

function scopesToArray(s: string): string[] {
  return s
    .split(/[,\s]+/)
    .map((x) => x.trim())
    .filter((x) => x.length > 0);
}

export function OAuthClientsPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const auth = useAuth();
  const qc = useQueryClient();

  const [createName, setCreateName] = React.useState("");
  const [createScopes, setCreateScopes] = React.useState("scrape:write");
  const [createActive, setCreateActive] = React.useState(true);

  const [createdSecret, setCreatedSecret] = React.useState<OAuthClientWithSecret | null>(null);
  const [rotatedSecret, setRotatedSecret] = React.useState<OAuthClientWithSecret | null>(null);

  const [issueClientId, setIssueClientId] = React.useState("");
  const [issueClientSecret, setIssueClientSecret] = React.useState("");
  const [issuedToken, setIssuedToken] = React.useState<TokenResponse | null>(null);

  const q = useQuery({
    queryKey: ["oauthClients"],
    queryFn: () => api.listOAuthClients(ctx),
  });

  const mCreate = useMutation({
    mutationFn: () =>
      api.createOAuthClient(ctx, {
        name: createName,
        scopes: scopesToArray(createScopes),
        is_active: createActive,
      }),
    onSuccess: (res) => {
      setCreatedSecret(res.client);
      void qc.invalidateQueries({ queryKey: ["oauthClients"] });
    },
  });

  const mRotate = useMutation({
    mutationFn: (clientId: string) => api.rotateOAuthClientSecret(ctx, clientId),
    onSuccess: (res) => {
      setRotatedSecret(res.client);
      void qc.invalidateQueries({ queryKey: ["oauthClients"] });
    },
  });

  const mRevoke = useMutation({
    mutationFn: (clientId: string) => api.revokeOAuthClient(ctx, clientId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["oauthClients"] });
    },
  });

  const mIssueToken = useMutation({
    mutationFn: () =>
      api.clientCredentialsToken(
        { baseUrl: ctx.baseUrl },
        { grant_type: "client_credentials", client_id: issueClientId, client_secret: issueClientSecret },
      ),
    onSuccess: (tr) => {
      setIssuedToken(tr);
      auth.setServiceToken(tr.access_token);
      auth.setUseServiceToken(true);
    },
  });

  async function copyText(s: string) {
    try {
      await navigator.clipboard.writeText(s);
    } catch {
      // ignore
    }
  }

  return (
    <div>
      <h1 className="pageTitle">外部連携</h1>
      <p className="pageDesc">外部の収集プログラムなどが接続するための認証情報を管理します。</p>

      <div className="grid2" style={{ marginBottom: 14 }}>
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">連携先を登録</h2>
          </div>

          {mCreate.error ? <ErrorBox error={mCreate.error} /> : null}

          <div className="row" style={{ alignItems: "stretch" }}>
            <label style={{ width: "100%" }}>
              <div className="small">連携先名</div>
              <input className="input" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            </label>

            <label style={{ width: "100%" }}>
              <div className="small">権限（カンマまたは空白区切り）</div>
              <input className="input" value={createScopes} onChange={(e) => setCreateScopes(e.target.value)} />
            </label>
          </div>

          <div className="row" style={{ marginTop: 10, justifyContent: "space-between" }}>
            <label className="small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={createActive} onChange={(e) => setCreateActive(e.target.checked)} />
              有効にする
            </label>

            <button className="btn primary" disabled={!createName || mCreate.isPending} onClick={() => mCreate.mutate()}>
              {mCreate.isPending ? "作成中…" : "登録する"}
            </button>
          </div>

          {createdSecret ? (
            <div style={{ marginTop: 12 }}>
              <div className="small">連携先を登録しました（認証キーは今回のみ表示されます）</div>
              <div className="card" style={{ marginTop: 8 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="small">連携先ID</div>
                  <button className="btn" onClick={() => copyText(createdSecret.client_id)}>
                    コピー
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{createdSecret.client_id}</div>

                <div className="row" style={{ justifyContent: "space-between", marginTop: 10 }}>
                  <div className="small">認証キー</div>
                  <button className="btn" onClick={() => copyText(createdSecret.client_secret)}>
                    コピー
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{createdSecret.client_secret}</div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">外部連携用トークンを発行</h2>
          </div>

          {mIssueToken.error ? <ErrorBox error={mIssueToken.error} /> : null}

          <div className="row" style={{ alignItems: "stretch" }}>
            <label style={{ width: "100%" }}>
              <div className="small">連携先ID</div>
              <input className="input" value={issueClientId} onChange={(e) => setIssueClientId(e.target.value)} />
            </label>

            <label style={{ width: "100%" }}>
              <div className="small">認証キー</div>
              <input
                className="input"
                value={issueClientSecret}
                onChange={(e) => setIssueClientSecret(e.target.value)}
              />
            </label>
          </div>

          <div className="row" style={{ marginTop: 10, justifyContent: "flex-end" }}>
            <button
              className="btn primary"
              disabled={!issueClientId || !issueClientSecret || mIssueToken.isPending}
              onClick={() => mIssueToken.mutate()}
            >
              {mIssueToken.isPending ? "発行中…" : "トークンを発行"}
            </button>
          </div>

          <div className="small" style={{ marginTop: 10 }}>
            発行したトークンは設定画面に保存され、認証方法が「外部連携」に切り替わります。
          </div>

          {issuedToken ? (
            <div style={{ marginTop: 10 }}>
              <div className="small">発行結果</div>
              <div className="card" style={{ marginTop: 6 }}>
                <JsonView value={issuedToken} />
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {q.isLoading ? <Loading label="連携先を読み込み中…" /> : null}
      {q.error ? <ErrorBox error={q.error} /> : null}

      {q.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">連携先一覧 ({q.data.items.length})</h2>
            <button className="btn" onClick={() => q.refetch()}>
              更新
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>連携先ID</th>
                <th>連携先名</th>
                <th>権限</th>
                <th>有効状態</th>
                <th>登録日時</th>
                <th>無効化日時</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((c) => (
                <tr key={c.client_id}>
                  <td style={{ fontFamily: "ui-monospace, monospace" }}>{c.client_id}</td>
                  <td>{c.name}</td>
                  <td>{c.scopes.join(" ")}</td>
                  <td>{c.is_active ? "有効" : "無効"}</td>
                  <td>{c.created_at}</td>
                  <td>{c.revoked_at ?? ""}</td>
                  <td>
                    <div className="row">
                      <button className="btn" onClick={() => mRotate.mutate(c.client_id)} disabled={mRotate.isPending}>
                        認証キーを再発行
                      </button>
                      <button className="btn danger" onClick={() => mRevoke.mutate(c.client_id)} disabled={mRevoke.isPending}>
                        無効にする
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {rotatedSecret ? (
            <div style={{ marginTop: 14 }}>
              <div className="small">再発行した認証キー（今回のみ表示されます）</div>
              <div className="card" style={{ marginTop: 8 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="small">連携先ID</div>
                  <button className="btn" onClick={() => copyText(rotatedSecret.client_id)}>
                    コピー
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{rotatedSecret.client_id}</div>

                <div className="row" style={{ justifyContent: "space-between", marginTop: 10 }}>
                  <div className="small">認証キー</div>
                  <button className="btn" onClick={() => copyText(rotatedSecret.client_secret)}>
                    コピー
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{rotatedSecret.client_secret}</div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
