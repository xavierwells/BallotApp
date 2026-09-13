import assert from "node:assert/strict";
import test from "node:test";
import { createSearchRequests } from "../app/search-request.ts";
import { filterPreviewRaces } from "../app/editorial/preview/preview-model.ts";
import { countyDirectoryLabel } from "../app/guides/browse-links.ts";

test("new search invalidates an older response and old cleanup cannot cancel the new one", () => {
  const requests = createSearchRequests();
  const old = requests.begin(() => assert.fail("unexpected timeout"));
  const current = requests.begin(() => assert.fail("unexpected timeout"));
  assert.equal(old.signal.aborted, true); assert.equal(old.isCurrent(), false);
  old.finish(); assert.equal(current.isCurrent(), true);
  current.finish(); assert.equal(current.isCurrent(), false);
  assert.equal(current.signal.aborted, false);
});

test("mode change cancels pending location callback before it can submit coordinates", () => {
  const requests = createSearchRequests();
  const location = requests.begin(() => assert.fail("unexpected timeout"));
  requests.cancel();
  assert.equal(location.isCurrent(), false); assert.equal(location.signal.aborted, true);
});

test("timeout releases loading state and invalidates any late result", async () => {
  const requests = createSearchRequests(5);
  let ticket;
  await new Promise(resolve => { ticket = requests.begin(resolve); });
  assert.equal(ticket.signal.aborted, true); assert.equal(ticket.isCurrent(), false);
});

test("repeated whitespace does not break phrase search or mutate the full race roster", () => {
  const race = { ballotTitle: "Synthetic Office", jurisdictionName: "Synthetic County", districtLabel: "District 24",
    candidates: [{ ballotLabel: "ALPHA  EXAMPLE", partyLabel: "Independent" }, { ballotLabel: "BETA EXAMPLE", partyLabel: "Green" }] };
  assert.deepEqual(filterPreviewRaces([race], " alpha   example "), [race]);
  assert.deepEqual(filterPreviewRaces([race], "DISTRICT   24"), [race]);
  assert.deepEqual(filterPreviewRaces([race], "GREEN"), [race]);
  assert.equal(filterPreviewRaces([race], "alpha")[0].candidates.length, 2);
  assert.equal(race.candidates[0].ballotLabel, "ALPHA  EXAMPLE");
  assert.equal(filterPreviewRaces([race], "invented name").length, 0);
  assert.equal(countyDirectoryLabel(" Coryell   County "), "Coryell County");
});
