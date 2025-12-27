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
          <div className="brandSub">Dashboard</div>
        </div>

        <nav className="nav">
          {navItems.map((it) => (
            <NavLink key={it.to} to={it.to} className={({ isActive }) => (isActive ? "navItem active" : "navItem")}>
              {it.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebarFooter">
          <div className="tokenInfo">
            <div className="tokenLabel">Token</div>
            <div className="tokenValue">{auth.activeToken ? "SET" : "NONE"}</div>
            <div className="tokenLabel">Mode</div>
            <div className="tokenValue">{auth.useServiceToken ? "Service" : "User"}</div>
          </div>

          <button className="btn" onClick={() => auth.logout()}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
