import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { PhaseType, PHASE_ORDER, PHASE_LABELS } from "@/types/project";

interface SDLCTimelineProps {
  currentPhase: PhaseType;
}

export function SDLCTimeline({ currentPhase }: SDLCTimelineProps) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-max">
        <div className="flex items-center">
          {PHASE_ORDER.map((phase, index) => {
            const isCompleted = index < currentIndex;
            const isCurrent = index === currentIndex;
            const isFuture = index > currentIndex;
            const isLast = index === PHASE_ORDER.length - 1;

            return (
              <div key={phase} className="flex items-center">
                <div className="flex flex-col items-center gap-2">
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all",
                      isCompleted &&
                        "border-emerald-500 bg-emerald-500 text-white",
                      isCurrent &&
                        "border-blue-600 bg-blue-600 text-white shadow-lg shadow-blue-200 ring-4 ring-blue-100",
                      isFuture &&
                        "border-slate-200 bg-slate-50 text-slate-300"
                    )}
                  >
                    {isCompleted ? (
                      <Check className="h-5 w-5" strokeWidth={2.5} />
                    ) : (
                      <span
                        className={cn(
                          "text-xs font-bold",
                          isCurrent && "text-white",
                          isFuture && "text-slate-300"
                        )}
                      >
                        {index + 1}
                      </span>
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-xs font-medium whitespace-nowrap",
                      isCompleted && "text-emerald-700",
                      isCurrent && "text-blue-700 font-semibold",
                      isFuture && "text-slate-400"
                    )}
                  >
                    {PHASE_LABELS[phase]}
                  </span>
                </div>
                {!isLast && (
                  <div
                    className={cn(
                      "mx-2 h-0.5 w-12 shrink-0 transition-all",
                      index < currentIndex
                        ? "bg-emerald-400"
                        : "bg-slate-200"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
