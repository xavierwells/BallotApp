import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import { areaGuideCounty, checkedDirectoryItems, countyDirectoryLabel, guideDirectoryHref, guideReleaseHref } from "../app/guides/browse-links.ts";
import { publicPages, staffPages, STAFF_HOME, STAFF_LOGIN } from "../app/editorial/staff-navigation.ts";

test("only reviewed county area results connect directly to real guides", () => {
  assert.equal(areaGuideCounty({ areaType: "county", name: "Coryell County" }, false), "Coryell County");
  assert.equal(areaGuideCounty({ areaType: "county", name: "Example County" }, true), null);
  for (const areaType of ["zip", "city", "precinct", "school_district"])
    assert.equal(areaGuideCounty({ areaType, name: "Coryell County" }, false), null);
});

test("stale or malformed API results cannot attach another county or an exact-ballot claim", () => {
  const item = { county: "Coryell County", releaseId: "id", exactMatch: false, completeBallot: false };
  assert.deepEqual(checkedDirectoryItems([item], " coryell county "), [item]);
  assert.deepEqual(checkedDirectoryItems([], "Missing County"), []);
  assert.throws(() => checkedDirectoryItems([item], "Lampasas County"));
  assert.throws(() => checkedDirectoryItems([{ ...item, exactMatch: true }]));
  assert.throws(() => checkedDirectoryItems(null));
});

test("explicit county entry only normalizes its display suffix, never guesses geography", () => {
  assert.equal(countyDirectoryLabel(" coryell "), "coryell County");
  assert.equal(countyDirectoryLabel("Coryell COUNTY"), "Coryell COUNTY");
  assert.equal(countyDirectoryLabel("Bell"), "Bell County");
  assert.equal(countyDirectoryLabel("Campbell"), "Campbell County");
  for (const query of ["", "  ", "county", "x".repeat(256)]) assert.equal(countyDirectoryLabel(query), null);
});

test("directory and release links have different meanings and encode all parameters", () => {
  assert.equal(guideDirectoryHref(), "/guides");
  assert.equal(guideDirectoryHref("Coryell County"), "/guides?county=Coryell+County");
  const id = "value&county=Other County";
  const link = new URL(guideReleaseHref(id), "https://example.test");
  assert.equal(link.searchParams.get("release"), id);
  assert.equal(link.searchParams.has("county"), false);
});

test("site map links refer only to actual site pages; login has one fixed internal destination", () => {
  assert.equal(STAFF_HOME, "/editorial/site-map");
  assert.equal(STAFF_LOGIN, "/editorial/login");
  const hrefs = [...staffPages, ...publicPages].map(page => page.href);
  assert.equal(new Set(hrefs).size, hrefs.length);
  for (const href of [...hrefs, STAFF_HOME, STAFF_LOGIN]) {
    assert.ok(href.startsWith("/") && !href.startsWith("//"));
    assert.ok(existsSync(new URL(`../app${href === "/" ? "" : href}/page.tsx`, import.meta.url)), href);
  }
});
