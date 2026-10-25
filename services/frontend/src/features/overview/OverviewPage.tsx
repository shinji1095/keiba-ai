import React from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { getApiBaseUrl } from "@/api/http";
import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";
import { statusLabel } from "@/shared/labels";

export function OverviewPage(): React.JSX.Element {
  const auth = useAuth();
  const baseUrl = getApiBaseUrl();

  const qHealth = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health({ baseUrl, token: null }),
  });

  return (
    <div>
      <h1 className="pageTitle">ホーム</h1>
      <p className="pageDesc">競馬データの閲覧や収集、システムの稼働状況を確認できます。</p>

      <div className="grid2">
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">システムの状態</h2>
            <span className={qHealth.data ? "pill ok" : "pill bad"}>{qHealth.data ? "正常" : "不明"}</span>
          </div>

          {qHealth.isLoading ? <Loading label="システムの状態を確認中…" /> : null}
          {qHealth.error ? <ErrorBox error={qHealth.error} /> : null}
          {qHealth.data ? <div className="small">稼働状態：{statusLabel(qHealth.data.status)}</div> : null}
        </div>

        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">接続・認証</h2>
            <span className="pill">{auth.activeToken ? "認証済み" : "未認証"}</span>
          </div>

          <div className="small">API接続先： {baseUrl}</div>
          <div className="small" style={{ marginTop: 10 }}>
            使用中の認証方法： {auth.useServiceToken ? "外部連携" : "ユーザー"}
          </div>

          <div style={{ marginTop: 14 }} className="small">
            よく使うページ
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <a className="btn" href="/scrape/status">稼働モニター</a>
            <a className="btn" href="/races">
              レース一覧
            </a>
            <a className="btn" href="/admin/oauth-clients">
              外部連携
            </a>
            <a className="btn" href="/scrape">
              データ収集
            </a>
          </div>

          <div style={{ marginTop: 14 }} className="small">
            ユーザー認証の有効期限が切れた場合は、自動で更新を試みます。
          </div>
        </div>
      </div>
    </div>
  );
}
