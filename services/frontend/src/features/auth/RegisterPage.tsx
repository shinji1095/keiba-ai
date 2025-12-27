import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/app/auth/useAuth";
import { ErrorBox } from "@/shared/ui/ErrorBox";

type LocState = { from?: string };

export function RegisterPage(): React.JSX.Element {
  const auth = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as LocState | null)?.from || "/";

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [error, setError] = React.useState<unknown>(null);
  const [busy, setBusy] = React.useState(false);

  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (passwordMismatch) return;

    setError(null);
    setBusy(true);
    try {
      await auth.register(username, password);
      nav(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 520, margin: "64px auto", padding: 16 }}>
      <h1 className="pageTitle">Register</h1>
      <p className="pageDesc">/auth/register を使用してユーザーを作成します。</p>

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

          <label style={{ width: "100%" }}>
            <div className="small">Confirm password</div>
            <input
              className="input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </label>
        </div>

        {passwordMismatch ? (
          <div className="small" style={{ marginTop: 8, color: "var(--danger)" }}>
            Passwords do not match.
          </div>
        ) : null}

        <div className="row" style={{ justifyContent: "flex-end", marginTop: 12 }}>
          <button
            className="btn primary"
            disabled={busy || !username || !password || !confirmPassword || passwordMismatch}
            type="submit"
          >
            {busy ? "Creating..." : "Create account"}
          </button>
        </div>

        <div className="small" style={{ marginTop: 10 }}>
          既にアカウントがある場合は <Link to="/login" state={{ from }}>ログイン</Link> してください。
        </div>
      </form>
    </div>
  );
}
