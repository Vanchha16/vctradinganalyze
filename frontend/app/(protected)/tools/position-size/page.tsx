"use client";

import { PageHeader } from "@/components/shared/page-header";
import { PositionSizeCalculator } from "@/features/tools/components/position-size-calculator";
import { PageContainer } from "@/features/dashboard/components/page-container";

export default function PositionSizeCalculatorPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Position Size Calculator"
          description="Enter balance, leverage, and lot size to get the max number of positions you can open."
        />
        <PositionSizeCalculator />
      </PageContainer>
    </div>
  );
}
