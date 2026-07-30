import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClaudeTrading AI",
  description: "ClaudeTrading AI application shell",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
