import React from "react";
import { Link } from "react-router-dom";

export function NotFoundPage(): React.JSX.Element {
  return (
    <div style={{ maxWidth: 620, margin: "64px auto", padding: 16 }}>
      <h1 className="pageTitle">404 Not Found</h1>
      <p className="pageDesc">ページが見つかりません。</p>
      <Link className="btn" to="/">
        Go home
      </Link>
    </div>
  );
}
