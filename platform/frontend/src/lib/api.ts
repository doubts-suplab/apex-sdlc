const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public title: string,
    public detail: string
  ) {
    super(title);
    this.name = "ApiError";
  }
}

// Bearer token for authenticated calls. Set by the persona-login flow (lib/auth.ts); attached to every
// request when present. Kept module-level so query/mutation hooks don't each thread it through.
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const problem = await res.json().catch(() => ({})) as Record<string, unknown>;
    // RFC 7807 problem details may be flat or nested under `detail`.
    const detailObj =
      problem["detail"] && typeof problem["detail"] === "object"
        ? (problem["detail"] as Record<string, unknown>)
        : problem;
    throw new ApiError(
      res.status,
      String(detailObj["title"] ?? problem["title"] ?? "Request failed"),
      String(detailObj["detail"] ?? problem["detail"] ?? res.statusText)
    );
  }
  return res.json() as Promise<T>;
}
