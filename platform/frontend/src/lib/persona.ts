"use client";

import { useState, useEffect, useCallback } from "react";
import { Persona, PersonaSchema } from "@/types/project";

const STORAGE_KEY = "apex_persona";
const DEFAULT_PERSONA: Persona = "developer";

export function usePersona() {
  const [persona, setPersonaState] = useState<Persona>(DEFAULT_PERSONA);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = PersonaSchema.safeParse(stored);
      if (parsed.success) {
        setPersonaState(parsed.data);
      }
    }
  }, []);

  const setPersona = useCallback((next: Persona) => {
    setPersonaState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  return { persona, setPersona, mounted };
}
