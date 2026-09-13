import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Private certification preview | What's on My Ballot",
  description: "Staff-only preview of imported certification records. Not a public or personalized ballot.",
  robots: { index: false, follow: false, nocache: true },
};

export default function PreviewLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
