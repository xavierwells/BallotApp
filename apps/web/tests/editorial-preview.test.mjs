import assert from "node:assert/strict";
import test from "node:test";
import { filterPreviewRaces, previewDate, sourceHref } from "../app/editorial/preview/preview-model.ts";

const races = [
  { id: "1", ballotTitle: "Example Office", jurisdictionName: "Example County", districtLabel: "District 4",
    candidates: [{ ballotLabel: "EXAMPLE ONE", partyLabel: "Independent" }, { ballotLabel: "EXAMPLE TWO", partyLabel: "Green" }] },
  { id: "2", ballotTitle: "Other Office", jurisdictionName: "Example State", districtLabel: null,
    candidates: [{ ballotLabel: "EXAMPLE THREE", partyLabel: "Republican" }] },
];

test("preview search preserves source order and whole race rosters", () => {
  assert.deepEqual(filterPreviewRaces(races, "office"), races);
  assert.deepEqual(filterPreviewRaces(races, " example one "), [races[0]]);
  assert.equal(filterPreviewRaces(races, "example one")[0].candidates.length, 2);
  assert.deepEqual(filterPreviewRaces(races, "district 4"), [races[0]]);
  assert.deepEqual(filterPreviewRaces(races, "Republican"), [races[1]]);
});

test("empty search and no-match remain explicit without invented entries", () => {
  assert.equal(filterPreviewRaces(races, "   "), races);
  assert.deepEqual(filterPreviewRaces(races, "missing"), []);
  assert.deepEqual(filterPreviewRaces([], "example"), []);
});

test("preview citation links reject executable and malformed protocols", () => {
  assert.equal(sourceHref("https://example.test/source.pdf"), "https://example.test/source.pdf");
  for (const value of ["javascript:alert(1)", "data:text/html,example", "file:///private.pdf", "/relative"])
    assert.equal(sourceHref(value), undefined);
});

test("election dates do not shift to the previous day in local time", () => {
  assert.equal(previewDate("2026-11-03"), "November 3, 2026");
  assert.equal(previewDate("invalid"), "Date unavailable");
});
