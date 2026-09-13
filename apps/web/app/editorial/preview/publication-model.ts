export type PublicationStatus = {
  batchId: string; canPublish: boolean; contentReady: boolean;
  blockers: { code: string; message: string }[]; basisHash: string | null;
  currentEventId: number | null; currentReleaseId: string | null;
  publishedBatchId: string | null; state: "unpublished" | "published" | "withdrawn";
};

export function publicationAction(status: PublicationStatus, batchId: string) {
  const alreadyPublished = status.state === "published" && status.publishedBatchId === batchId;
  return {
    canPublish: status.canPublish && status.contentReady && Boolean(status.basisHash) && !alreadyPublished,
    canWithdraw: status.canPublish && status.state === "published" && Boolean(status.currentReleaseId),
    label: alreadyPublished ? "This revision is published" : status.state === "published" ? "Replace published guide" : "Publish county guide",
  };
}
