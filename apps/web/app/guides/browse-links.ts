import type { GuideSummary } from "./guide-model";

export function checkedDirectoryItems(items: GuideSummary[], county?: string): GuideSummary[] {
  // A stale API image may ignore a newly added filter. Do not attach another
  // county's guide to an area card if the API/web versions disagree.
  if (!Array.isArray(items) || items.some(item => !item || item.exactMatch !== false || item.completeBallot !== false ||
      typeof item.releaseId !== "string" || typeof item.county !== "string" ||
      (county !== undefined && item.county.trim().toLowerCase() !== county.trim().toLowerCase())))
    throw new Error("The guide service returned an incompatible directory response. The operator may need to rebuild the API as well as the website.");
  return items;
}

export function countyDirectoryLabel(value: string): string | null {
  const label = value.trim().replace(/\s+/g, " ");
  if (!label || label.length > 248 || label.toLowerCase() === "county") return null;
  // Only an explicitly chosen county may omit the display suffix. No fuzzy
  // matching, hard-coded ZIP map, address parsing, or inferred city coverage.
  return /\bcounty$/i.test(label) ? label : `${label} County`;
}

export function guideDirectoryHref(county?: string): string {
  return county ? `/guides?${new URLSearchParams({ county })}` : "/guides";
}

export function guideReleaseHref(releaseId: string): string {
  return `/guides?${new URLSearchParams({ release: releaseId })}`;
}

export function areaGuideCounty(area: { areaType: string; name: string }, demonstration: boolean): string | null {
  return !demonstration && area.areaType === "county" ? area.name : null;
}
