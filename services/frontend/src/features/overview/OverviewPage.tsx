import React from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { getApiBaseUrl } from "@/api/http";
import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";
import { JsonView } from "@/shared/ui/JsonView";

export function OverviewPage(): React.JSX.Element {
  const ctx = useApiCtx();
  const auth = useAuth();
  const baseUrl = getApiBaseUrl();

  const qHealth = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health({ baseUrl, token: null }),
  });

  return (
    <div>
      <h1 className="pageTitle">Overview</h1>
      <p className="pageDesc">OpenAPI (21_openapi.yaml) に記載されたエンドポイント向けの管理画面です。</p>

      <div className="grid2">
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">System</h2>
            <span className={qHealth.data ? "pill ok" : "pill bad"}>{qHealth.data ? "OK" : "UNKNOWN"}</span>
          </div>

          {qHealth.isLoading ? <Loading label="Loading /health..." /> : null}
          {qHealth.error ? <ErrorBox error={qHealth.error} /> : null}
          {qHealth.data ? <JsonView value={qHealth.data} /> : null}
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">Client</h2>
            <span className="pill">{auth.activeToken ? "AUTHENTICATED" : "NO TOKEN"}</span>
          </div>

          <div className="small">API base URL: {baseUrl}</div>
          <div className="small" style={{ marginTop: 10 }}>
            Active token mode: {auth.useServiceToken ? "Service" : "User"}
          </div>

          <div style={{ marginTop: 14 }} className="small">
            よく使うページ
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <a className="btn" href="/races">
              Races
            </a>
            <a className="btn" href="/admin/oauth-clients">
              OAuth Clients
            </a>
            <a className="btn" href="/scrape">
              Scrape Console
            </a>
          </div>

          <div style={{ marginTop: 14 }} className="small">
            401 の場合、User token 使用中のみ /auth/refresh を自動呼び出しします。
          </div>
        </div>
      </div>
    </div>
  );
}
