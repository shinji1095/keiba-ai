import React from "react";
import { useQuery } from "@tanstack/react-query";

import { ErrorBox } from "@/shared/ui/ErrorBox";
import { Loading } from "@/shared/ui/Loading";
import { MarkdownView } from "@/shared/ui/MarkdownView";

type ManifestRace = {
  race_id: string;
  race_date: string;
  baba_code: number;
  race_no: number;
  venue_name: string;
  files: Array<{
    name: string;
    title: string;
    description: string;
  }>;
};

type Manifest = {
  races: ManifestRace[];
};

async function fetchManifest(): Promise<Manifest> {
  const res = await fetch("/docs/test/data/manifest.json");
  if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
  return res.json();
}

async function fetchMarkdown(race_id: string, filename: string): Promise<string> {
  const res = await fetch(`/docs/test/data/${race_id}/${filename}`);
  if (!res.ok) throw new Error(`markdown fetch failed: ${res.status}`);
  return res.text();
}

export function TestDataPage(): React.JSX.Element {
  const [selectedRace, setSelectedRace] = React.useState<string | null>(null);
  const [selectedFile, setSelectedFile] = React.useState<string | null>(null);

  const qManifest = useQuery({
    queryKey: ["testDataManifest"],
    queryFn: fetchManifest,
  });

  const qMarkdown = useQuery({
    queryKey: ["testDataMarkdown", selectedRace, selectedFile],
    queryFn: () => fetchMarkdown(selectedRace!, selectedFile!),
    enabled: !!selectedRace && !!selectedFile,
  });

  const currentRace = qManifest.data?.races.find((r) => r.race_id === selectedRace);

  return (
    <div>
      <h1 className="pageTitle">Test Data Viewer</h1>
      <p className="pageDesc">docs/test/data/ の正規化データを閲覧します（TDD用フィクスチャ）。</p>

      {qManifest.isLoading ? <Loading label="Loading manifest..." /> : null}
      {qManifest.error ? <ErrorBox error={qManifest.error} /> : null}

      {qManifest.data ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">Races ({qManifest.data.races.length})</h2>
          </div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            {qManifest.data.races.map((r) => (
              <button
                key={r.race_id}
                className={selectedRace === r.race_id ? "btn primary" : "btn"}
                onClick={() => {
                  setSelectedRace(r.race_id);
                  setSelectedFile(null);
                }}
              >
                {r.venue_name} {r.race_date} {r.race_no}R
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {currentRace ? (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cardHeader">
            <h2 className="cardTitle">
              {currentRace.venue_name} {currentRace.race_date} {currentRace.race_no}R
            </h2>
          </div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            {currentRace.files.map((f) => (
              <button
                key={f.name}
                className={selectedFile === f.name ? "btn primary" : "btn"}
                onClick={() => setSelectedFile(f.name)}
                title={f.description}
              >
                {f.title}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {qMarkdown.isLoading ? <Loading label="Loading..." /> : null}
      {qMarkdown.error ? <ErrorBox error={qMarkdown.error} /> : null}

      {qMarkdown.data ? (
        <div className="card">
          <div className="cardHeader">
            <h2 className="cardTitle">{selectedFile}</h2>
            <button className="btn" onClick={() => qMarkdown.refetch()}>
              Refresh
            </button>
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.5 }}>
            <MarkdownView content={qMarkdown.data} />
          </div>
        </div>
      ) : null}
    </div>
  );
}





