import type { Metadata } from "next";
import "./globals.css";

const description = "A local project by Xavier Wells to bring Copperas Cove ballot information together, with sources you can check. Coverage is still being built.";

export const metadata: Metadata = {
  metadataBase: new URL("https://copperascovevotes.org"),
  title: "What's on My Ballot?",
  description,
  openGraph: { title: "What's on My Ballot? — Copperas Cove", description, type: "website", siteName: "Copperas Cove Votes" },
  twitter: { card: "summary_large_image", title: "What's on My Ballot? — Copperas Cove", description },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
