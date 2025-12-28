import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";

type LocState = { from?: string };

export function LoginPage(): React.JSX.Element {
  const auth = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as LocState | null)?.from || "/";

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<unknown>(null);
  const [busy, setBusy] = React.useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await auth.login(username, password);
      nav(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 520, margin: "64px auto", padding: 16 }}>
      <h1 className="pageTitle">Login</h1>
      <p className="pageDesc">/auth/login を使用してログインし、access token を保持します。</p>

      {error ? <ErrorBox error={error} /> : null}

      <form className="card" onSubmit={onSubmit}>
        <div className="row" style={{ alignItems: "stretch" }}>
          <label style={{ width: "100%" }}>
            <div className="small">Username</div>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>

          <label style={{ width: "100%" }}>
            <div className="small">Password</div>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        </div>

        <div className="row" style={{ justifyContent: "flex-end", marginTop: 12 }}>
          <Link className="btn" to="/register" state={{ from }}>
            Sign up
          </Link>
          <button className="btn primary" disabled={busy || !username || !password} type="submit">
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          Refresh token は HttpOnly Cookie を前提としており、この画面では表示されません。
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          アカウント未作成の場合は <Link to="/register" state={{ from }}>ユーザー登録</Link> してください。
        </div>
      </form>
    </div>
  );
}
