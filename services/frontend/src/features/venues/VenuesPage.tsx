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
      <h1 className="pageTitle">Venues</h1>
      <p className="pageDesc">/venues (GET): 競馬場コード一覧</p>

      {q.isLoading ? <Loading label="Loading venues..." /> : null}
      {q.error ? <ErrorBox error={q.error} /> : null}

      {venues.length > 0 ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">items ({venues.length})</h2>
            <button className="btn" onClick={() => q.refetch()}>
              Refresh
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>baba_code</th>
                <th>venue_name</th>
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
