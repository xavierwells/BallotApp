import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "What's on My Ballot?",
  description: "Every race. Every candidate. Every proposition. Explained and sourced.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
