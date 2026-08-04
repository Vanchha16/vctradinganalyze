import { cn } from "@/lib/utils";

/** ClaudeTrading AI logomark - zigzag chart-arrow, matches the uploaded brand logo's shape/color DNA. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={cn("size-4", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.1"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 19 10.5 7l3 6L20 5" />
      <path d="M15.4 5H20v4.6" />
      <circle cx="4" cy="19" r="1.9" fill="currentColor" stroke="none" />
      <circle cx="10.5" cy="7" r="1.9" fill="currentColor" stroke="none" />
      <circle cx="13.5" cy="13" r="1.9" fill="currentColor" stroke="none" />
    </svg>
  );
}
