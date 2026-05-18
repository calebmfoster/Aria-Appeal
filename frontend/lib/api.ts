import { API_URL } from "@/lib/config";

export class UnauthorizedError extends Error {
  constructor() {
    super("Session expired");
    this.name = "UnauthorizedError";
  }
}

export async function apiFetch(
  path: string,
  init: RequestInit & { token?: string } = {}
): Promise<Response> {
  const { token, headers: initHeaders, ...rest } = init;
  const headers = new Headers(initHeaders);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...rest, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("aria:unauthorized"));
    }
    throw new UnauthorizedError();
  }

  return res;
}
