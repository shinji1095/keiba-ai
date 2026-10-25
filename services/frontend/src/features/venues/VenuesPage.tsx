import React from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/endpoints";
import { useApiCtx } from "@/app/hooks/useApiCtx";
import { mergeVenues } from "@/shared/venues";
import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";

export function VenuesPage(): React.JSX.Element {
  const ctx = useApiCtx();

  const q = useQuery({
    queryKey: ["venues"],
    queryFn: () => api.listVenues(ctx),
  });

  const venues = mergeVenues(q.data?.items);

  return (
    <div>
      <h1 className="pageTitle">競馬場一覧</h1>
      <p className="pageDesc">競馬場の名前とコードを確認できます。</p>

      {q.isLoading ? <Loading label="競馬場を読み込み中…" /> : null}
      {q.error ? <ErrorBox error={q.error} /> : null}

      {venues.length > 0 ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">競馬場一覧 ({venues.length})</h2>
            <button className="btn" onClick={() => q.refetch()}>
              更新
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>競馬場コード</th>
                <th>競馬場名</th>
              </tr>
            </thead>
            <tbody>
              {venues.map((v) => (
                <tr key={v.baba_code}>
                  <td>{v.baba_code}</td>
                  <td>{v.venue_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
