import type { Metadata } from "next";

import { AuthCard } from "@/features/auth/components/auth-card";
import { LoginForm } from "@/features/auth/components/login-form";

export const metadata: Metadata = { title: "Sign in - ClaudeTrading AI" };

/**
 * No "create an account" link (Phase 8E, docs/59 §9) - accounts are
 * admin-provisioned only, `POST /auth/register` returns `403`.
 */
export default function LoginPage() {
  return (
    <AuthCard title="Sign in" description="Access your ClaudeTrading AI dashboard.">
      <LoginForm />
    </AuthCard>
  );
}
