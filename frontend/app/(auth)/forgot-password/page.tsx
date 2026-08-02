import type { Metadata } from "next";

import { AuthCard } from "@/features/auth/components/auth-card";
import { ForgotPasswordNotice } from "@/features/auth/components/forgot-password-notice";

export const metadata: Metadata = { title: "Forgot password - ClaudeTrading AI" };

export default function ForgotPasswordPage() {
  return (
    <AuthCard title="Forgot password" description="Reset your password.">
      <ForgotPasswordNotice />
    </AuthCard>
  );
}
