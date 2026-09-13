"use client";

import { useEffect, useRef, useState } from "react";
import { filterPreviewRaces, previewDate, sourceHref } from "./preview-model";
import type { GuidePreview, PreviewSummary } from "./preview-model";
import styles from "./preview.module.css";
import PublicationPanel from "./publication-panel";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/editorial`;
const sourceLink = (batchId: string, page: number | null) =>
  `${API}/batches/${encodeURIComponent(batchId)}/source${page ? `#page=${page}` : ""}`;

export default function GuidePreviewPage() {
  const [staff, setStaff] = useState<{ username: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [items, setItems] = useState<PreviewSummary[]>([]);
  const [releases, setReleases] = useState<{ batchId: string; releaseId: string; county: string; publishedAt: string }[]>([]);
  const [releaseError, setReleaseError] = useState("");
  const [releaseReload, setReleaseReload] = useState(0);
  const [selected, setSelected] = useState("");
  const [preview, setPreview] = useState<GuidePreview | null>(null);
  const [query, setQuery] = useState("");
  const [reload, setReload] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);

  function clearPrivateView() {
    setStaff(null); setItems([]); setSelected(""); setPreview(null); setQuery("");
    setReleases([]); setReleaseError("");
  }

  async function read(path: string, signal: AbortSignal) {
    const response = await fetch(API + path, { credentials: "include", cache: "no-store", signal });
    if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
    if (response.status === 401) {
      clearPrivateView();
      throw new Error("Sign in to the editorial workspace to view imported records.");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(typeof body.detail === "string" ? body.detail : "Could not load the private preview. Please retry.");
    }
    return response.json();
  }

  useEffect(() => {
    const controller = new AbortController();
    clearPrivateView(); setLoading(true); setError("");
    (async () => {
      try {
        const identity = await read("/me", controller.signal);
        const imported = await read("/guide-preview", controller.signal);
        if (!controller.signal.aborted) { setStaff(identity); setItems(imported); }
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not connect to the editorial service.");
      } finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
    // Only reload on mount or explicit retry; no background voter tracking.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload]);

  useEffect(() => {
    if (!staff) return;
    const controller = new AbortController();
    setReleaseError("");
    read("/guide-releases", controller.signal).then(value => {
      if (!controller.signal.aborted) setReleases(value);
    }).catch(reason => {
      if (!controller.signal.aborted) { setReleases([]); setReleaseError(reason instanceof Error ? reason.message : "Could not load publication controls."); }
    });
    return () => controller.abort();
    // Keep withdrawal reachable independently of the current import preview.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staff, releaseReload]);

  useEffect(() => {
    if (!selected || !staff) return;
    const controller = new AbortController();
    setBusy(true); setError(""); setPreview(null); setQuery("");
    read(`/guide-preview/${encodeURIComponent(selected)}`, controller.signal).then(value => {
      if (!controller.signal.aborted) setPreview(value);
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not open this county.");
    }).finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
    // Abort older selections so their responses cannot replace the new county.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, staff]);

  useEffect(() => { if (preview) heading.current?.focus(); }, [preview]);
  useEffect(() => {
    // Back/forward cache must not restore a private view after a session ended.
    const hide = () => { setPreview(null); setItems([]); setReleases([]); setSelected(""); };
    const show = (event: PageTransitionEvent) => { if (event.persisted) setReload(value => value + 1); };
    window.addEventListener("pagehide", hide); window.addEventListener("pageshow", show);
    return () => { window.removeEventListener("pagehide", hide); window.removeEventListener("pageshow", show); };
  }, []);

  async function signOut() {
    setBusy(true); setPreview(null); setSelected(""); setQuery(""); setError("");
    try {
      const response = await fetch(API + "/logout", { method: "POST", credentials: "include", cache: "no-store" });
      if (!response.ok) throw new Error("Sign-out failed. Please retry.");
      clearPrivateView();
    } catch { setError("Sign-out failed. Please retry."); }
    finally { setBusy(false); }
  }

  const visible = filterPreviewRaces(preview?.races ?? [], query);
  return <main className={styles.workspace}>
    <header className={styles.header}>
      <div><a href="/editorial/site-map">← Staff site map</a>{" · "}<a href="/editorial">County review</a><h1>Certification guide preview</h1>
        <p>Real imported records, in a readable guide. For staff only.</p></div>
      {staff && <div className={styles.account}><span>Signed in as {staff.username}</span>
        <button className={styles.secondary} disabled={busy} onClick={signOut}>Sign out</button></div>}
    </header>
    <aside className={styles.scope} aria-label="Preview limitations">
      <strong>Private staff preview · Publication controlled separately · Not your ballot</strong>
      <p>This certification lists candidates by county. It is not a complete ballot and does not establish
        which races apply to an address. Local races, propositions, official ballot styles and voting
        information may be missing. Browsing this page does not publish or approve anything.</p>
    </aside>
    {error && <div className={styles.error} role="alert"><p>{error}</p>
      <button className={styles.secondary} onClick={() => { setBusy(false); setReload(value => value + 1); }}>Reload preview</button></div>}
    {loading ? <p role="status">Checking staff access…</p> : !staff ?
      <section className={styles.empty}><h2>Staff sign-in required</h2>
        <p>Sign in, then choose Preview and publishing from the staff site map.</p>
        <a href="/editorial/login">Open staff sign-in</a></section> : <>
      <section aria-label="Imported county certifications" className={styles.counties}>
        {items.map(item => <button key={item.batchId} className={styles.county} aria-pressed={selected === item.batchId}
          onClick={() => { if (selected !== item.batchId) { setPreview(null); setSelected(item.batchId); } }}>
          <strong>{item.county}</strong><span>{previewDate(item.electionDate)}</span>
          <span>{item.raceCount} races · {item.candidateCount} candidate entries</span>
          <span>Imported · Private preview</span>
        </button>)}
      </section>
      {releaseError && <p className={styles.error} role="alert">{releaseError} <button className={styles.secondary} onClick={() => setReleaseReload(value => value + 1)}>Retry publication list</button></p>}
      {releases.length > 0 && <details className={styles.source}><summary>Manage published releases ({releases.length})</summary>
        <p className={styles.small}>Use these controls even if a newer draft exists or the canonical preview cannot load. Source approval can separately prevent public display.</p>
        {releases.map(release => <p key={release.releaseId}><button className={styles.secondary}
          onClick={() => { if (selected !== release.batchId) { setPreview(null); setSelected(release.batchId); } }}>Manage {release.county}</button> · Published {previewDate(release.publishedAt)}</p>)}
      </details>}
      {items.length === 0 && <section className={styles.empty}><h2>No current imported certifications yet</h2>
        <p>Finish county-source confirmation and select Import reviewed county in the review workspace.
          A newer unimported draft also hides its older import from this list.</p>
        <a href="/editorial">Return to county review</a></section>}
      {!selected && items.length > 0 && <p>Choose a county to explore its imported certification. This is not a location match.</p>}
      {busy && selected && <p role="status">Loading imported records…</p>}
      {selected && <PublicationPanel key={selected} batchId={selected}
        county={items.find(item => item.batchId === selected)?.county ?? releases.find(item => item.batchId === selected)?.county ?? "selected county"}
        onChanged={() => setReleaseReload(value => value + 1)}
        onSessionExpired={() => { clearPrivateView(); setError("Your session expired. Sign in again before publishing."); }} />}
      {preview && <section aria-label={`${preview.county} certification guide`}>
        {!preview.current && <p className={styles.scope}>Historical import: a newer review draft exists. This revision is not current.</p>}
        <div className={styles.intro}><p className={styles.eyebrow}>Candidate certification · {previewDate(preview.electionDate)}</p>
          <h2 ref={heading} tabIndex={-1}>{preview.county}</h2><p>{preview.electionName}</p>
          <p>{preview.raceCount} races · {preview.candidateCount} candidate entries in this county&apos;s certification.
            Shared races repeat across counties; these are not distinct-person totals.</p>
          <p className={styles.small}>Revision {preview.revision} · Imported by {preview.importedBy} on {previewDate(preview.importedAt)}.
            Review details below describe the saved import, not a fresh source check.</p>
          {preview.countySourceConfirmedBy && <p className={styles.small}>County source coverage confirmed by {preview.countySourceConfirmedBy} at import.</p>}
          {!preview.reviewReceiptAvailable && <p className={styles.scope}>This older import has no saved review-detail snapshot. No reviewer or review date has been inferred.</p>}
        </div>
        <details className={styles.source}><summary>Source document and import evidence</summary>
          <p>{preview.source.title}</p>
          <p><a href={sourceLink(preview.batchId, null)} target="_blank" rel="noreferrer">Open retained source PDF</a>
            {sourceHref(preview.source.url) && <> · <a href={sourceHref(preview.source.url)} target="_blank" rel="noreferrer">Publisher&apos;s document</a></>}</p>
          <p className={styles.small}>SHA-256: <code>{preview.source.checksum}</code></p>
          <p className={styles.small}>Source order is preserved below; this is not official ballot order.
            Check the printed citation when opening a PDF. Unknown viewer offsets require manual navigation.</p>
        </details>
        <div className={styles.search}><label htmlFor="preview-search">Find an office or candidate in this county</label>
          <input id="preview-search" type="search" maxLength={200} autoComplete="off" value={query}
            onChange={event => setQuery(event.target.value)} placeholder="Search office, name, district or party" />
          <p role="status" className={styles.small}>{visible.length} of {preview.races.length} races shown.
            Search keeps every candidate in each matching race.</p></div>
        {visible.length === 0 && <p>No matching races in this certification. <button className={styles.secondary} onClick={() => setQuery("")}>Clear search</button></p>}
        <div className={styles.races}>{visible.map(race => <article className={styles.race} key={race.id}>
          <p className={styles.eyebrow}>{race.governmentLevel} · {race.jurisdictionName}</p>
          <h3>{race.ballotTitle}</h3>
          {race.districtLabel && <p className={styles.small}>{race.districtLabel}</p>}
          <table><caption className={styles.srOnly}>Certified candidates for {race.ballotTitle}</caption>
            <thead><tr><th scope="col">Candidate</th><th scope="col">Party as certified</th></tr></thead>
            <tbody>{race.candidates.map(candidate => <tr key={candidate.id}><td>{candidate.ballotLabel}</td><td>{candidate.partyLabel}</td></tr>)}</tbody>
          </table>
          <p className={styles.citation}><a href={sourceLink(preview.batchId, race.pdfPageNumber)} target="_blank" rel="noreferrer">
            Source: printed page {race.sourcePage}</a> · {race.pdfPageNumber ? `PDF page ${race.pdfPageNumber}` : "Find printed page manually"}</p>
          <details className={styles.review}><summary>{race.reviewStatusAtImport === "reviewed" ? "Review evidence at import" : "Review details unavailable"}</summary>
            <p className={styles.small}>These are historical recorded acceptances, not a new verification or an assessment of current reviewer eligibility.</p>
            {race.recordedAcceptances.length === 0 && <p className={styles.small}>No individual acceptance details are available in this receipt.</p>}
            <ul>{race.recordedAcceptances.map((review, index) => <li key={`${review.kind}-${review.decisionId}-${index}`}>
              {review.kind === "shared" ? `Shared content review from ${review.county}` : "Recorded local acceptance"}
              {": "}{review.reviewer} · {previewDate(review.at)} · <a href={sourceLink(review.batchId, review.pdfPageNumber)} target="_blank" rel="noreferrer">printed page {review.sourcePage}</a>
            </li>)}</ul>
          </details>
          <p className={styles.missing}>Names and parties only. Candidate statements, biographies and office explainers are not included in this preview.</p>
        </article>)}</div>
      </section>}
    </>}
  </main>;
}
