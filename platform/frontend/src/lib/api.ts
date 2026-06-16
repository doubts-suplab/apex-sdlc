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

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const problem = await res.json().catch(() => ({})) as Record<string, string>;
    throw new ApiError(
      res.status,
      problem["title"] ?? "Request failed",
      problem["detail"] ?? res.statusText
    );
  }
  return res.json() as Promise<T>;
}
