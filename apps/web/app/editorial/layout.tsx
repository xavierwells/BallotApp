import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Staff workspace | What's on My Ballot",
  robots: { index: false, follow: false, nocache: true },
};

export default function EditorialLayout({ children }: Readonly<{ children: React.ReactNode }>) { return children; }
