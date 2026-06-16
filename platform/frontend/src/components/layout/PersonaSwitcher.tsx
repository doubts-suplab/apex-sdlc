"use client";

import { ChevronDown, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePersona } from "@/lib/persona";
import { Persona, PERSONA_LABELS } from "@/types/project";

const PERSONA_OPTIONS: Persona[] = [
  "developer",
  "ba",
  "qa",
  "pm",
  "lead",
  "architect",
  "ciso",
];

export function PersonaSwitcher() {
  const { persona, setPersona, mounted } = usePersona();

  if (!mounted) {
    return (
      <div className="h-9 w-36 animate-pulse rounded-md bg-slate-200" />
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <User className="h-4 w-4" />
          <span>{PERSONA_LABELS[persona]}</span>
          <ChevronDown className="h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          View as persona
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {PERSONA_OPTIONS.map((p) => (
          <DropdownMenuItem
            key={p}
            onSelect={() => setPersona(p)}
            className={
              p === persona
                ? "bg-accent text-accent-foreground font-medium"
                : ""
            }
          >
            {PERSONA_LABELS[p]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
