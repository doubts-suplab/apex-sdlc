import { Badge } from "@/components/ui/badge";
import { LLMProvider } from "@/types/integration";
import { cn } from "@/lib/utils";
import { Cpu } from "lucide-react";

const PROVIDER_STYLES: Record<LLMProvider, string> = {
  anthropic: "bg-purple-100 text-purple-800 border-purple-200",
  ollama: "bg-green-100 text-green-800 border-green-200",
  groq: "bg-orange-100 text-orange-800 border-orange-200",
  huggingface: "bg-yellow-100 text-yellow-800 border-yellow-200",
};

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  anthropic: "Anthropic",
  ollama: "Ollama",
  groq: "Groq",
  huggingface: "HuggingFace",
};

function isLLMProvider(value: string): value is LLMProvider {
  return ["anthropic", "ollama", "groq", "huggingface"].includes(value);
}

export function LLMProviderBadge() {
  const rawProvider = process.env.NEXT_PUBLIC_LLM_PROVIDER ?? "anthropic";
  const provider: LLMProvider = isLLMProvider(rawProvider)
    ? rawProvider
    : "anthropic";

  const model = process.env.NEXT_PUBLIC_LLM_MODEL ?? "";
  const label = PROVIDER_LABELS[provider];
  const title = model ? `${label} · ${model}` : label;

  return (
    <Badge
      variant="outline"
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        PROVIDER_STYLES[provider]
      )}
      title={title}
    >
      <Cpu className="h-3 w-3" />
      {label}
      {model && (
        <span className="font-normal opacity-75 truncate max-w-[120px]">
          {model}
        </span>
      )}
    </Badge>
  );
}
