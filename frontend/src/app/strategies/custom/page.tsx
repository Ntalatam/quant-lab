import { Suspense } from "react";

import { StrategyStudio } from "@/components/strategies/StrategyStudio";

export default function CustomStrategyStudioPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-2 text-sm text-text-muted">
          Loading strategy studio…
        </div>
      }
    >
      <StrategyStudio />
    </Suspense>
  );
}
