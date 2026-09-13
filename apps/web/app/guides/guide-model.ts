import type { PreviewRace } from "../editorial/preview/preview-model";

export type GuideSummary = {
  releaseId: string; county: string; electionName: string; electionDate: string;
  publishedAt: string; raceCount: number; candidateCount: number; exactMatch: false; completeBallot: false;
};
export type PublicGuide = GuideSummary & {
  scope: "county_certification_guide";
  source: { title: string; publisherName: string; url: string; checksum: string; publishedAt: string | null; retrievedAt: string };
  races: (Omit<PreviewRace, "reviewStatusAtImport" | "recordedAcceptances"> & { reviewedAt: string })[];
};

export function publisherPageLink(value: string, page: number | null): string | undefined {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return undefined;
    if (page && Number.isInteger(page) && page > 0) url.hash = `page=${page}`;
    return url.href;
  } catch { return undefined; }
}
