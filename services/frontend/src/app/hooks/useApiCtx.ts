import { ApiCtx } from "@/api/endpoints";
import { getApiBaseUrl } from "@/api/http";
import { useAuth } from "../auth/useAuth";

export function useApiCtx(): ApiCtx {
  const auth = useAuth();
  const baseUrl = getApiBaseUrl();

  return {
    baseUrl,
    token: auth.activeToken,
    onUnauthorized: auth.useServiceToken ? undefined : async () => auth.refresh(),
  };
}
