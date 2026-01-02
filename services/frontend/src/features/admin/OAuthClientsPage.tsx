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
      <h1 className="pageTitle">OAuth Clients</h1>
      <p className="pageDesc">/admin/oauth-clients と /auth/token（client_credentials）</p>

      <div className="grid2" style={{ marginBottom: 14 }}>
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Create client</h2>
          </div>

          {mCreate.error ? <ErrorBox error={mCreate.error} /> : null}

          <div className="row" style={{ alignItems: "stretch" }}>
            <label style={{ width: "100%" }}>
              <div className="small">name</div>
              <input className="input" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            </label>

            <label style={{ width: "100%" }}>
              <div className="small">scopes (comma/space)</div>
              <input className="input" value={createScopes} onChange={(e) => setCreateScopes(e.target.value)} />
            </label>
          </div>

          <div className="row" style={{ marginTop: 10, justifyContent: "space-between" }}>
            <label className="small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={createActive} onChange={(e) => setCreateActive(e.target.checked)} />
              is_active
            </label>

            <button className="btn primary" disabled={!createName || mCreate.isPending} onClick={() => mCreate.mutate()}>
              {mCreate.isPending ? "Creating..." : "Create"}
            </button>
          </div>

          {createdSecret ? (
            <div style={{ marginTop: 12 }}>
              <div className="small">Created (secret is shown once)</div>
              <div className="card" style={{ marginTop: 8 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="small">client_id</div>
                  <button className="btn" onClick={() => copyText(createdSecret.client_id)}>
                    Copy
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{createdSecret.client_id}</div>

                <div className="row" style={{ justifyContent: "space-between", marginTop: 10 }}>
                  <div className="small">client_secret</div>
                  <button className="btn" onClick={() => copyText(createdSecret.client_secret)}>
                    Copy
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{createdSecret.client_secret}</div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Issue service token</h2>
          </div>

          {mIssueToken.error ? <ErrorBox error={mIssueToken.error} /> : null}

          <div className="row" style={{ alignItems: "stretch" }}>
            <label style={{ width: "100%" }}>
              <div className="small">client_id</div>
              <input className="input" value={issueClientId} onChange={(e) => setIssueClientId(e.target.value)} />
            </label>

            <label style={{ width: "100%" }}>
              <div className="small">client_secret</div>
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
              {mIssueToken.isPending ? "Issuing..." : "Issue token"}
            </button>
          </div>

          <div className="small" style={{ marginTop: 10 }}>
            発行した access token は Settings の Service Token に保存され、token mode を Service に切り替えます。
          </div>

          {issuedToken ? (
            <div style={{ marginTop: 10 }}>
              <div className="small">TokenResponse</div>
              <div className="card" style={{ marginTop: 6 }}>
                <JsonView value={issuedToken} />
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {q.isLoading ? <Loading label="Loading oauth clients..." /> : null}
      {q.error ? <ErrorBox error={q.error} /> : null}

      {q.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Clients ({q.data.items.length})</h2>
            <button className="btn" onClick={() => q.refetch()}>
              Refresh
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>client_id</th>
                <th>name</th>
                <th>scopes</th>
                <th>active</th>
                <th>created</th>
                <th>revoked</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((c) => (
                <tr key={c.client_id}>
                  <td style={{ fontFamily: "ui-monospace, monospace" }}>{c.client_id}</td>
                  <td>{c.name}</td>
                  <td>{c.scopes.join(" ")}</td>
                  <td>{c.is_active ? "true" : "false"}</td>
                  <td>{c.created_at}</td>
                  <td>{c.revoked_at ?? ""}</td>
                  <td>
                    <div className="row">
                      <button className="btn" onClick={() => mRotate.mutate(c.client_id)} disabled={mRotate.isPending}>
                        Rotate secret
                      </button>
                      <button className="btn danger" onClick={() => mRevoke.mutate(c.client_id)} disabled={mRevoke.isPending}>
                        Revoke
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {rotatedSecret ? (
            <div style={{ marginTop: 14 }}>
              <div className="small">Rotated secret (shown once)</div>
              <div className="card" style={{ marginTop: 8 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="small">client_id</div>
                  <button className="btn" onClick={() => copyText(rotatedSecret.client_id)}>
                    Copy
                  </button>
                </div>
                <div style={{ fontFamily: "ui-monospace, monospace" }}>{rotatedSecret.client_id}</div>

                <div className="row" style={{ justifyContent: "space-between", marginTop: 10 }}>
                  <div className="small">client_secret</div>
                  <button className="btn" onClick={() => copyText(rotatedSecret.client_secret)}>
                    Copy
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
