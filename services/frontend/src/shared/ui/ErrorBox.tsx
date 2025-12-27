import React from "react";
import { ApiHttpError } from "@/api/http";

export function ErrorBox({ error }: { error: unknown }): React.JSX.Element {
  const msg = React.useMemo(() => {
    if (!error) return "Unknown error";
    if (typeof error === "string") return error;
    if (error instanceof ApiHttpError) return `${error.message} (status=${error.status})`;
    if (error instanceof Error) return error.message;
    return "Unknown error";
  }, [error]);

  return <div className="alert">{msg}</div>;
}
