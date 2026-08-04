"use client";

import { useEffect, useState } from "react";
import { apiFetch, setAuthToken } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import { Persona } from "@/types/project";

// Personas allowed to perform approval writes (mirrors the backend's _APPROVER_PERSONAS).
const APPROVER_PERSONAS: Persona[] = ["lead", "ba", "architect", "ciso"];

export function isApprover(persona: Persona): boolean {
  return APPROVER_PERSONAS.includes(persona);
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  persona: string;
}

/**
 * Persona-login: mint a bearer token for the currently-selected persona and register it on the API
 * client, so authenticated calls (journey persist, project metrics) carry the persona for RBAC.
 * Re-mints whenever the persona changes. This is a dev/identity-broker login — no credential yet.
 */
export function useAuthToken() {
  const { persona, mounted } = usePersona();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;
    setReady(false);
    (async () => {
      try {
        const res = await apiFetch<TokenResponse>("/auth/token", {
          method: "POST",
          body: JSON.stringify({ subject: `${persona}@apex.local`, persona }),
        });
        if (!cancelled) {
          setAuthToken(res.access_token);
          setReady(true);
        }
      } catch {
        if (!cancelled) {
          setAuthToken(null);
          setReady(true); // resolve anyway; unauthenticated calls will surface 401/403
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [persona, mounted]);

  return { persona, isApprover: isApprover(persona), ready };
}
