import React from "react";
import { NavLink, Outlet } from "react-router-dom";

import { navItems } from "./nav";
import { useAuth } from "../auth/useAuth";

export function AppShell(): React.JSX.Element {
  const auth = useAuth();

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="sidebarHeader">
          <div className="brand">競馬AI</div>
          <div className="brandSub">管理画面</div>
        </div>

        <nav className="nav">
          {navItems.map((it) => (
            <NavLink key={it.to} to={it.to} end={it.to === "/scrape"} className={({ isActive }) => (isActive ? "navItem active" : "navItem")}>
              {it.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebarFooter">
          <div className="tokenInfo">
            <div className="tokenLabel">認証情報</div>
            <div className="tokenValue">{auth.activeToken ? "設定済み" : "未設定"}</div>
            <div className="tokenLabel">認証方法</div>
            <div className="tokenValue">{auth.useServiceToken ? "外部連携" : "ユーザー"}</div>
          </div>

          <button className="btn" onClick={() => auth.logout()}>
            ログアウト
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
