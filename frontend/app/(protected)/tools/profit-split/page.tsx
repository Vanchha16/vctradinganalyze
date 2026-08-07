"use client";

import { PageHeader } from "@/components/shared/page-header";
import { ProfitSplitCalculator } from "@/features/tools/components/profit-split-calculator";
import { PageContainer } from "@/features/dashboard/components/page-container";

export default function ProfitSplitCalculatorPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Profit Split Calculator"
          description="Split a final pot proportionally across contributors by their original stake."
        />
        <ProfitSplitCalculator />
      </PageContainer>
    </div>
  );
}
