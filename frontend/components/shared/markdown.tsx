import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/**
 * Shared LLM-text renderer (ADR-108) - AI Analysis reasoning and AI Chat
 * messages both render markdown, so the styling is defined once here
 * instead of duplicated per feature. No `@tailwindcss/typography` plugin
 * is installed (not part of ADR-108's scope), so headings/lists/etc are
 * styled manually via `components` overrides instead of a `prose` class.
 * No `rehype-raw` - content is LLM-generated text only, never raw HTML.
 */
const components: Components = {
  p: ({ className, ...props }) => <p className={cn("mb-3 last:mb-0", className)} {...props} />,
  ul: ({ className, ...props }) => (
    <ul className={cn("mb-3 ml-4 list-disc space-y-1.5 last:mb-0", className)} {...props} />
  ),
  ol: ({ className, ...props }) => (
    <ol className={cn("mb-3 ml-4 list-decimal space-y-1.5 last:mb-0", className)} {...props} />
  ),
  li: ({ className, ...props }) => <li className={cn("leading-relaxed", className)} {...props} />,
  strong: ({ className, ...props }) => <strong className={cn("font-semibold text-foreground", className)} {...props} />,
  h1: ({ className, ...props }) => <h3 className={cn("mb-1.5 mt-4 text-base font-semibold first:mt-0", className)} {...props} />,
  h2: ({ className, ...props }) => <h3 className={cn("mb-1.5 mt-4 text-base font-semibold first:mt-0", className)} {...props} />,
  h3: ({ className, ...props }) => <h3 className={cn("mb-1.5 mt-4 text-base font-semibold first:mt-0", className)} {...props} />,
  code: ({ className, ...props }) => (
    <code className={cn("rounded bg-muted px-1 py-0.5 font-mono text-sm", className)} {...props} />
  ),
  a: ({ className, ...props }) => (
    // eslint-disable-next-line jsx-a11y/anchor-has-content
    <a
      className={cn("text-primary underline underline-offset-2 hover:text-primary/80", className)}
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
};

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("text-sm leading-[1.75]", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
