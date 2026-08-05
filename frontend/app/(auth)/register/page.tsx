import { redirect } from "next/navigation";

/**
 * Phase 8E (docs/59 §9, ADR-119) - public registration is removed.
 * `/register` is not deleted outright (an unexpectedly-vanished route is a
 * worse failure mode than a redirect for anyone with the URL bookmarked/
 * linked) - it unconditionally sends every visitor to `/login`, same
 * treatment for authenticated and unauthenticated visitors alike.
 */
export default function RegisterPage() {
  redirect("/login");
}
