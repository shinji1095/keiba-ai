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
      <h1 className="pageTitle">ログイン</h1>
      <p className="pageDesc">ユーザー名とパスワードを入力してログインしてください。</p>

      {error ? <ErrorBox error={error} /> : null}

      <form className="card" onSubmit={onSubmit}>
        <div className="row" style={{ alignItems: "stretch" }}>
          <label style={{ width: "100%" }}>
            <div className="small">ユーザー名</div>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>

          <label style={{ width: "100%" }}>
            <div className="small">パスワード</div>
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
            ユーザー登録
          </Link>
          <button className="btn primary" disabled={busy || !username || !password} type="submit">
            {busy ? "ログイン中…" : "ログイン"}
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          ログインの有効期限は自動で更新されます。
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          アカウント未作成の場合は <Link to="/register" state={{ from }}>ユーザー登録</Link> してください。
        </div>
      </form>
    </div>
  );
}
