export type ReviewableSection = {
  key: string;
  sourcePage: string;
  reviewStatus: "unreviewed" | "reviewed" | "flagged";
};

export type ReviewPage = {
  sourcePage: string;
  total: number;
  reviewed: number;
  flagged: number;
  pending: number;
  complete: boolean;
};

export function reviewPages(
  races: readonly ReviewableSection[],
  drafts: Readonly<Record<string, unknown>> = {},
): ReviewPage[] {
  const pages = new Map<string, ReviewPage>();
  for (const race of races) {
    const page = pages.get(race.sourcePage) ?? {
      sourcePage: race.sourcePage, total: 0, reviewed: 0, flagged: 0, pending: 0, complete: false,
    };
    page.total += 1;
    if (race.reviewStatus === "reviewed") page.reviewed += 1;
    if (race.reviewStatus === "flagged") page.flagged += 1;
    if (Object.hasOwn(drafts, race.key)) page.pending += 1;
    pages.set(race.sourcePage, page);
  }
  // Use source order, including non-numeric citations. Unsaved choices never
  // turn a page complete or hide a pending edit on a previously reviewed page.
  return [...pages.values()].map(page => ({ ...page, complete: page.reviewed === page.total && page.pending === 0 }));
}

export function firstUnfinishedPage(races: readonly ReviewableSection[]): string | null {
  return reviewPages(races).find(page => !page.complete)?.sourcePage ?? null;
}

export function pageAfterSubmission(races: readonly ReviewableSection[], current: string): string | null {
  const pages = reviewPages(races);
  const index = pages.findIndex(page => page.sourcePage === current);
  // Flags, corrections and partial reviews still need attention. Stay on them.
  if (index >= 0 && !pages[index].complete) return current;
  const remaining = index < 0 ? pages : [...pages.slice(index + 1), ...pages.slice(0, index)];
  return remaining.find(page => !page.complete)?.sourcePage ?? null;
}
