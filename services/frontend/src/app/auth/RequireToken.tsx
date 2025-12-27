import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./useAuth";

export function RequireToken({ children }: { children: React.ReactNode }): React.JSX.Element {
  const auth = useAuth();
  const loc = useLocation();

  if (!auth.activeToken) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  return <>{children}</>;
}
