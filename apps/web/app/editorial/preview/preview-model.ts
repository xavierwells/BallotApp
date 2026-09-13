export type PreviewSummary = {
  batchId: string; county: string; revision: number; electionName: string;
  electionDate: string; importedAt: string; raceCount: number; candidateCount: number;
};
export type PreviewAcceptance = {
  kind: "local" | "shared"; reviewer: string; at: string; decisionId: string;
  county: string; batchId: string; sourcePage: string; pdfPageNumber: number | null;
};
export type PreviewRace = {
  id: string; key: string; ballotTitle: string; governmentLevel: string;
  jurisdictionName: string; districtLabel: string | null; seatsAvailable: number;
  sourcePage: string; pdfPageNumber: number | null;
  candidates: { id: string; ballotLabel: string; partyLabel: string }[];
  reviewStatusAtImport: "reviewed" | "unavailable";
  recordedAcceptances: PreviewAcceptance[];
};
export type GuidePreview = PreviewSummary & {
  scope: "private_certification_preview"; exactMatch: false; publicationAllowed: false;
  current: boolean; importedBy: string; countySourceConfirmedBy: string | null;
  reviewReceiptAvailable: boolean;
  source: { title: string; url: string; checksum: string }; races: PreviewRace[];
};

export function filterPreviewRaces<T extends Pick<PreviewRace, "ballotTitle" | "jurisdictionName" | "districtLabel" | "candidates">>(races: T[], query: string): T[] {
  const normalize = (value: string) => value.trim().replace(/\s+/g, " ").toLocaleLowerCase("en-US");
  const term = normalize(query);
  if (!term) return races;
  // Search changes visibility, never the candidate roster or source order.
  return races.filter(race => [race.ballotTitle, race.jurisdictionName, race.districtLabel ?? "",
    ...race.candidates.flatMap(candidate => [candidate.ballotLabel, candidate.partyLabel])]
    .some(value => normalize(value).includes(term)));
}

export function sourceHref(value: string): string | undefined {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch { return undefined; }
}

export function previewDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric", timeZone: "UTC",
  });
}
