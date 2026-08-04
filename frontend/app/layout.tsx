import type { Metadata } from "next";
import { Inter_Tight, JetBrains_Mono } from "next/font/google";
import "./globals.css";

import { Toaster } from "sonner";

import { AuthProvider } from "@/providers/auth-provider";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";
import { cn } from "@/lib/utils";

// Premium design system typeface (Inter Tight / JetBrains Mono) - self-hosted
// by next/font at build time, zero runtime network request. Exposed as CSS
// variables so tailwind.config.ts's fontFamily extension can reference them.
const sans = Inter_Tight({ variable: "--font-sans", subsets: ["latin"] });
const mono = JetBrains_Mono({ variable: "--font-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ClaudeTrading AI",
  description: "ClaudeTrading AI application shell",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: required by next-themes - the `class`
    // attribute is set client-side before hydration (docs/53 §7).
    <html lang="en" suppressHydrationWarning>
      <body className={cn(sans.variable, mono.variable, "font-sans")}>
        {/* enableSystem intentionally omitted: the reference UI is hard-dark
            by default with no OS-preference detection (its own theme hook
            only reads/writes localStorage) - `enableSystem` here previously
            let a light-mode OS override `defaultTheme`, which is why a
            fresh/no-stored-preference browser rendered light. */}
        <ThemeProvider attribute="class" defaultTheme="dark" disableTransitionOnChange>
          <QueryProvider>
            <AuthProvider>
              {children}
              {/* Mounted once - every call site uses lib/toast.ts's wrapper instead of importing sonner directly. */}
              <Toaster richColors position="top-right" />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
