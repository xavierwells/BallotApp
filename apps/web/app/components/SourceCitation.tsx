export type SourceCitationData = {
  title: string;
  publisherName: string;
  sourceUrl: string;
  retrievedAt: string;
  sourcePage?: string;
  publicAccessLevel: "metadata_only" | "public_copy";
};

type SourceCitationProps = {
  citation: SourceCitationData;
};

/**
 * Displays source metadata without ever revealing a private retained artifact.
 * Ballot and editorial views will supply this data from their published API
 * representation once document-query endpoints are introduced.
 */
export function SourceCitation({ citation }: SourceCitationProps) {
  const retrievalTime = new Date(citation.retrievedAt);

  return (
    <aside className="source-citation" aria-label={`Source: ${citation.title}`}>
      <p className="source-citation-label">Official source</p>
      <p className="source-citation-title">
        <a href={citation.sourceUrl} rel="noreferrer" target="_blank">
          {citation.title}
        </a>
      </p>
      <p className="source-citation-details">
        {citation.publisherName}
        {citation.sourcePage ? ` · Page ${citation.sourcePage}` : ""}
        {Number.isNaN(retrievalTime.getTime())
          ? " · Retrieval time unavailable"
          : ` · Retrieved ${retrievalTime.toLocaleDateString("en-US", { timeZone: "UTC" })}`}
      </p>
      {citation.publicAccessLevel === "metadata_only" && (
        <p className="source-citation-notice">
          Source document retained for verification; view it at the official link.
        </p>
      )}
    </aside>
  );
}
