import assert from "node:assert/strict";
import test from "node:test";
import { publicationAction } from "../app/editorial/preview/publication-model.ts";
import { publisherPageLink } from "../app/guides/guide-model.ts";
import { filterPreviewRaces } from "../app/editorial/preview/preview-model.ts";

const status = { batchId: "new", canPublish: true, contentReady: true, basisHash: "hash",
  state: "unpublished", currentEventId: null, currentReleaseId: null, publishedBatchId: null, blockers: [] };

test("publication needs both permission and ready evidence", () => {
  assert.equal(publicationAction(status, "new").canPublish, true);
  assert.equal(publicationAction({ ...status, canPublish: false }, "new").canPublish, false);
  assert.equal(publicationAction({ ...status, contentReady: false }, "new").canPublish, false);
  assert.equal(publicationAction({ ...status, basisHash: null }, "new").canPublish, false);
});
test("already published, replacement, and withdrawal remain distinct", () => {
  const published = { ...status, state: "published", currentReleaseId: "release", currentEventId: 5, publishedBatchId: "old" };
  assert.equal(publicationAction(published, "old").canPublish, false);
  assert.equal(publicationAction(published, "new").label, "Replace published guide");
  assert.equal(publicationAction({ ...published, contentReady: false }, "new").canWithdraw, true);
  assert.equal(publicationAction({ ...published, canPublish: false }, "new").canWithdraw, false);
  assert.equal(publicationAction({ ...published, state: "withdrawn" }, "new").canWithdraw, false);
});
test("public citations point only to publishers, never staff source paths", () => {
  assert.equal(publisherPageLink("https://example.test/source.pdf#old", 12), "https://example.test/source.pdf#page=12");
  for (const link of ["javascript:alert(1)", "file:///private.pdf", "/api/v1/editorial/batches/source", "https://secret:token@example.test/file"])
    assert.equal(publisherPageLink(link, 1), undefined);
});
test("public guide search requires no private review fields and preserves every candidate", () => {
  const races = [{ ballotTitle: "Example Office", jurisdictionName: "Example County", districtLabel: null,
    candidates: [{ id: "a", ballotLabel: "Alpha", partyLabel: "Independent" }, { id: "b", ballotLabel: "Beta", partyLabel: "Green" }] }];
  assert.equal(filterPreviewRaces(races, "alpha")[0].candidates.length, 2);
  assert.deepEqual(filterPreviewRaces(races, "no match"), []);
});
