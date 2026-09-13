"use client";

import { useEffect, useState } from "react";
import { filterPreviewRaces, previewDate } from "../editorial/preview/preview-model";
import { publisherPageLink } from "./guide-model";
import type { PublicGuide, GuideSummary } from "./guide-model";
import styles from "../editorial/preview/preview.module.css";
import { checkedDirectoryItems, guideReleaseHref } from "./browse-links";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/guides`;

export default function CountyGuidesPage() {
  const [items, setItems] = useState<GuideSummary[]>([]);
  const [guide, setGuide] = useState<PublicGuide | null>(null);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reading, setReading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [reload, setReload] = useState(0);
  const [county, setCounty] = useState<string | undefined>(undefined);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    setSelected(new URLSearchParams(window.location.search).get("release") ?? "");
    setCounty(new URLSearchParams(window.location.search).get("county") || undefined);
    setInitialized(true);
    const restore = (event: PageTransitionEvent) => { if (event.persisted) setReload(value => value + 1); };
    const hide = () => { setGuide(null); setItems([]); setQuery(""); };
    window.addEventListener("pageshow", restore); window.addEventListener("pagehide", hide);
    return () => { window.removeEventListener("pageshow", restore); window.removeEventListener("pagehide", hide); };
  }, []);

  useEffect(() => {
    if (!initialized) return;
    const controller = new AbortController();
    setLoading(true); setListError("");
    if (offset === 0) setItems([]);
    const parameters = new URLSearchParams({ offset: String(offset), limit: "20", ...(county ? { county } : {}) });
    fetch(`${API}?${parameters}`, { cache: "no-store", credentials: "omit", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("Published guides could not be loaded. Please retry.");
        const value = await response.json();
        const next = checkedDirectoryItems(value.items, county);
        if (!controller.signal.aborted) {
          setItems(previous => offset === 0 ? next : [...previous, ...next.filter(item => !previous.some(old => old.releaseId === item.releaseId))]);
          setHasMore(value.hasMore);
        }
      }).catch(cause => { if (!controller.signal.aborted) setListError(cause instanceof Error ? cause.message : "Could not connect to the guide service."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, reload, county, initialized]);

  useEffect(() => {
    const controller = new AbortController();
    setGuide(null); setQuery(""); setError("");
    if (!selected) { setReading(false); return () => controller.abort(); }
    setReading(true);
    fetch(`${API}/${encodeURIComponent(selected)}`, { cache: "no-store", credentials: "omit", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 404
          ? "This guide is no longer published at this link. Choose an available guide below; it may have been replaced or withdrawn."
          : "This guide could not be loaded. Please retry.");
        const value = await response.json();
        if (!controller.signal.aborted) setGuide(value);
      }).catch(cause => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Could not connect to the guide service."); })
      .finally(() => { if (!controller.signal.aborted) setReading(false); });
    return () => controller.abort();
  }, [selected, reload]);

  function refresh() { setOffset(0); setReload(value => value + 1); }
  const races = filterPreviewRaces(guide?.races ?? [], query);
  return <main className={styles.workspace}>
    <header className={styles.header}><div><a href="/">← BallotApp home</a><h1>County election guides</h1>
      <p>Reviewed candidate names, offices and parties from official certification records.</p></div>
      <button className={styles.secondary} disabled={loading || reading} onClick={refresh}>Refresh guides</button></header>
    <aside className={styles.scope} aria-label="Guide coverage limitations"><strong>County-wide information · Not your exact ballot</strong>
      <p>Not every race listed here applies to every voter in the county. These guides are not complete ballots:
        local races, propositions, ballot styles and voting information may be missing. Confirm your personal ballot with your election office.</p></aside>
    {listError && <p className={styles.error} role="alert">{listError}</p>}
    {county && <p>County directory filter: <strong>{county}</strong>. <a href="/guides">Show all counties</a></p>}
    <nav className={styles.counties} aria-label="Published county guides">{items.map(item =>
      <a key={item.releaseId} className={styles.county} href={guideReleaseHref(item.releaseId)} aria-current={selected === item.releaseId ? "page" : undefined}>
        <strong>{item.county}</strong><span>{previewDate(item.electionDate)}</span><span>{item.raceCount} races · {item.candidateCount} candidate entries</span>
      </a>)}</nav>
    {loading && <p role="status">Loading published guides…</p>}
    {!loading && !listError && items.length === 0 && <section className={styles.empty}><h2>No county guides currently published{county ? ` for ${county}` : ""}</h2>
      <p>Private review material is not shown here. An empty list does not mean there are no elections or candidates.</p></section>}
    {hasMore && !loading && !listError && <button className={styles.secondary} onClick={() => setOffset(value => value + 20)}>More county guides</button>}
    {error && <p className={styles.error} role="alert">{error}</p>}
    {reading && <p role="status">Loading the published guide…</p>}
    {guide && <section aria-label={`${guide.county} published guide`}>
      <div className={styles.intro}><p className={styles.eyebrow}>Candidate certification · {previewDate(guide.electionDate)}</p><h2>{guide.county}</h2>
        <p>{guide.electionName}</p><p className={styles.small}>Published {previewDate(guide.publishedAt)}. This is a dated release, not a live check of the source.</p>
        <p>{guide.raceCount} races · {guide.candidateCount} candidate entries. Shared races can appear in multiple county guides.</p></div>
      <details className={styles.source}><summary>Official source and dates</summary><p>{guide.source.title} · {guide.source.publisherName}</p>
        <p><a href={publisherPageLink(guide.source.url, null)} target="_blank" rel="noreferrer">Open the publisher&apos;s document</a></p>
        <p className={styles.small}>Source published: {guide.source.publishedAt ? previewDate(guide.source.publishedAt) : "Not recorded"} · Retrieved {previewDate(guide.source.retrievedAt)}.</p>
        <p className={styles.small}>Source SHA-256: <code>{guide.source.checksum}</code></p>
        <p className={styles.small}>Links open the original publisher&apos;s site. BallotApp does not provide a public PDF copy. Source order is not official ballot order.</p></details>
      <div className={styles.search}><label htmlFor="guide-search">Find an office, candidate or party</label>
        <input id="guide-search" type="search" maxLength={200} autoComplete="off" value={query} onChange={event => setQuery(event.target.value)} />
        <p className={styles.small} role="status">{races.length} of {guide.races.length} races shown. Each matching race keeps its full candidate list.</p></div>
      {races.length === 0 && <p>No matching races. <button className={styles.secondary} onClick={() => setQuery("")}>Clear search</button></p>}
      <div className={styles.races}>{races.map(race => <article className={styles.race} key={race.id}>
        <p className={styles.eyebrow}>{race.governmentLevel} · {race.jurisdictionName}</p><h3>{race.ballotTitle}</h3>
        {race.districtLabel && <p>{race.districtLabel}</p>}
        <table><caption className={styles.srOnly}>Certified candidates for {race.ballotTitle}</caption>
          <thead><tr><th scope="col">Candidate</th><th scope="col">Party as certified</th></tr></thead>
          <tbody>{race.candidates.map(candidate => <tr key={candidate.id}><td>{candidate.ballotLabel}</td><td>{candidate.partyLabel}</td></tr>)}</tbody></table>
        <p className={styles.citation}><a href={publisherPageLink(guide.source.url, race.pdfPageNumber)} target="_blank" rel="noreferrer">Source: printed page {race.sourcePage}</a>
          {race.pdfPageNumber ? ` · PDF page ${race.pdfPageNumber}` : " · Find the printed page manually"}</p>
        <p className={styles.small}>Content review recorded {previewDate(race.reviewedAt)}. This date is not a new source check.</p>
        <p className={styles.missing}>Candidate statements, biographies and office explainers are not included.</p>
      </article>)}</div>
      <p><a href="/contribute">How to report a mistake</a> · Independent project, not an official election website or endorsement.</p>
    </section>}
  </main>;
}
