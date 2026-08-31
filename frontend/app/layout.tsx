import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northstar · Purchase review",
  description: "Chat through a software purchase. One agent, a new hat at each step.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
