"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import styles from "./review.module.css";
import { editTranscription, fieldCorrections, sectionSubmission } from "./review-draft";
import type { SectionChoice, SectionDraft } from "./review-draft";
import { firstUnfinishedPage, pageAfterSubmission, reviewPages } from "./review-navigation";
import StaffLogin from "./staff-login";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/editorial`;
type Staff = { username: string };
type Race = {
  key: string; ballotTitle: string; jurisdictionName: string; districtLabel: string | null;
  sourcePage: string; pdfPageNumber: number | null;
  reviewStatus: "unreviewed" | "reviewed" | "flagged"; approvalCount: number;
  candidates: { ballotLabel: string; partyLabel: string }[];
  decisions: { reviewer: string; decision: string; note: string; at: string; carriedForward?: boolean }[];
  countySourceReviewed: boolean;
  matchingCounties: string[];
  sharedReviewBlockedReason: string | null;
  sharedReviews: { decisionId: string; reviewer: string; at: string; county: string;
    batchId: string; sourcePage: string; pdfPageNumber: number | null }[];
  corrections: { reviewer: string; at: string; note: string;
    changes: { field: string; candidateIndex: number | null; before: string; after: string }[] }[];
};
type Batch = {
  id: string; county: string; revision: number; current: boolean; imported: boolean;
  reviewedRaces: number; raceCount: number; candidateCount: number; requiredReviewers: number;
  election: { name: string; date: string }; source: { title: string; url: string; checksum: string }; races: Race[];
  sharedReviewedRaces: number; requiresCountyConfirmation: boolean; reviewBasisHash: string;
  countySourceConfirmedBy: string | null;
};
const statusLabel = { unreviewed: "Awaiting review", reviewed: "Reviewed", flagged: "Needs attention" };

export default function EditorialPage() {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batch, setBatch] = useState<Batch | null>(null);
  const [page, setPage] = useState("");
  const [drafts, setDrafts] = useState<Record<string, SectionDraft>>({});
  const [countyConfirmed, setCountyConfirmed] = useState(false);
  const hasPending = Object.keys(drafts).length > 0;
  const requestVersion = useRef(0);
  const reviewHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => { setCountyConfirmed(false); }, [batch?.id, batch?.reviewBasisHash]);

  useEffect(() => {
    if (!batch) return;
    reviewHeading.current?.focus({ preventScroll: true });
    reviewHeading.current?.scrollIntoView({ block: "start" });
    // After a page transition, put keyboard/screen-reader focus at the new work.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batch?.id, page]);

  async function api(path: string, init: RequestInit = {}) {
    const response = await fetch(API + path, { ...init, credentials: "include", cache: "no-store",
      headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers } });
    if (response.status === 401) {
      setStaff(null); setBatch(null); setBatches([]); setDrafts({});
    }
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Please check the form and try again.");
    return result;
  }

  useEffect(() => {
    if (!hasPending) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasPending]);

  useEffect(() => {
    let active = true;
    fetch(API + "/me", { credentials: "include", cache: "no-store" }).then(async response => {
      if (response.status === 401) return;
      if (!response.ok) throw new Error("The editorial service is unavailable. Check that setup and migrations finished.");
      const identity = await response.json();
      if (active) setStaff(identity);
    }).catch(() => { if (active) setError("Could not connect to the editorial service. Check the API is running."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!staff) return;
    let active = true;
    api("/batches").then(value => { if (active) setBatches(value); })
      .catch(reason => { if (active) setError(reason.message); });
    return () => { active = false; };
    // Load this publication's queue after a successful sign-in.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staff]);

  async function openBatch(id: string) {
    if (hasPending && !window.confirm("Discard your unsubmitted decisions and corrections before opening another task?")) return;
    setDrafts({});
    const version = ++requestVersion.current;
    setBusy(true); setError(""); setNotice(""); setBatch(null);
    try {
      const next: Batch = await api(`/batches/${id}`);
      if (version !== requestVersion.current) return;
      setBatch(next); setPage(next.imported ? "" : firstUnfinishedPage(next.races) ?? "");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not open this review task."); }
    finally { if (version === requestVersion.current) setBusy(false); }
  }

  function switchPage(next: string) {
    if (next === page) return;
    const target = reviewPages(batch?.races ?? [], drafts).find(item => item.sourcePage === next);
    if (!target) return;
    if (target.complete && !window.confirm(`This page's content has already been reviewed (page ${next}). Open it again to inspect the source or flag a correction? Existing approvals will not be reset.`)) return;
    setPage(next); setNotice("");
  }

  function changeDraft(race: Race, changes: Partial<SectionDraft>) {
    const saved = race.decisions.find(item => item.reviewer === staff?.username);
    setNotice("");
    setDrafts(previous => ({ ...previous, [race.key]: {
      ...(previous[race.key] ?? { decision: "flagged", note: saved?.decision === "flagged" ? saved.note : "", editing: false, edits: {} }),
      ...changes,
    } }));
  }

  function editField(race: Race, field: string, value: string) {
    const saved = race.decisions.find(item => item.reviewer === staff?.username);
    if (!batch?.current || batch.imported || busy || (drafts[race.key]?.decision ?? saved?.decision) !== "flagged") return;
    setNotice("");
    setDrafts(previous => {
      const next = { ...previous };
      const edited = editTranscription(race, previous[race.key], field, value, saved);
      if (edited) next[race.key] = edited;
      else delete next[race.key];
      return next;
    });
  }

  async function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!batch) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const sections = sectionSubmission(batch.races, drafts);
      if (!sections.length) return;
      const updated: Batch = await api(`/batches/${batch.id}/review`, { method: "POST",
        body: JSON.stringify({ sections, confirmed: true }) });
      setBatch(updated); setBatches(previous => previous.map(item => item.id === batch.id ? updated : item));
      const nextPage = pageAfterSubmission(updated.races, page);
      setPage(nextPage ?? "");
      const savedNotice = sections.some(section => section.corrections.length) ?
        "Saved. Corrected sections remain flagged until you compare and accept the updated text. Unchanged reviews were preserved." :
        "Section decisions saved. Nothing was published.";
      setNotice(savedNotice + (nextPage === null ? " All page content is reviewed. County source confirmation and import remain separate." :
        nextPage !== page ? ` Opened unfinished page ${nextPage}.` : " This page still has content needing review or attention."));
      setDrafts({});
      // Shared review can change progress in other counties without writing any
      // review under their names. Refresh the queue after a successful save.
      try { setBatches(await api("/batches")); }
      catch { setError("Your review was saved, but county progress could not refresh. Reopen the task when the service is available."); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save the review."); }
    finally { setBusy(false); }
  }

  async function importReviewed() {
    if (!batch || hasPending) return;
    if (batch.requiresCountyConfirmation && !countyConfirmed) return;
    setBusy(true); setError("");
    try {
      const updated = await api(`/batches/${batch.id}/import`, { method: "POST",
        body: JSON.stringify({ confirmedCountyCoverage: countyConfirmed, reviewBasisHash: batch.reviewBasisHash }) });
      setBatch(updated); setBatches(previous => previous.map(item => item.id === updated.id ? updated : item));
      setPage("");
      setNotice("Reviewed facts imported. Public ballot publication is a separate step.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not import this draft."); }
    finally { setBusy(false); }
  }

  const pages = reviewPages(batch?.races ?? [], drafts);
  const currentPage = pages.find(item => item.sourcePage === page);
  const visible = batch?.races.filter(race => race.sourcePage === page) ?? [];
  const pdfPage = visible[0]?.pdfPageNumber;
  const sourceUrl = batch ? `${API}/batches/${batch.id}/source${pdfPage ? `#page=${pdfPage}` : ""}` : "";

  return <main className={styles.workspace}>
    <header className={styles.header}>
      <div><a href="/editorial/site-map">← Staff site map</a>{" · "}<a href="/">Homepage</a><h1>Editorial workspace</h1>
        <p>Check official facts against their source, one section at a time.</p></div>
      {staff && <div className={styles.account}><span>Signed in as {staff.username}</span>
        <button disabled={busy} className={styles.secondary} onClick={async () => {
          if (hasPending && !window.confirm("Discard your unsubmitted decisions and corrections and sign out?")) return;
          setBusy(true);
          try { await api("/logout", { method: "POST" }); setStaff(null); setBatch(null); setBatches([]); setDrafts({}); setNotice(""); }
          catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-out failed. Please retry."); }
          finally { setBusy(false); }
        }}>Sign out</button></div>}
    </header>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {notice && <p role="status" className={styles.notice}>{notice}</p>}
    {loading ? <p role="status">Opening workspace…</p> : !staff ?
      <StaffLogin /> : <>
      <p><a href="/editorial/preview">Private guide preview</a> · Browse imported records without changing reviews or publishing.</p>
      <section aria-label="County review tasks" className={styles.queue}>
        {batches.length === 0 && <p>No review tasks yet. Run the documented pilot setup to load the downloaded certification.</p>}
        {batches.map(item => <button key={item.id} disabled={busy} aria-pressed={batch?.id === item.id}
          className={`${styles.task} ${batch?.id === item.id ? styles.active : ""}`} onClick={() => openBatch(item.id)}>
          <strong>{item.county}</strong><span>{item.raceCount} races · {item.candidateCount} candidate entries</span>
          <span>{item.imported ? "Imported · publication managed in preview" : `${item.reviewedRaces} of ${item.raceCount} race contents reviewed`}</span>
          {!!item.sharedReviewedRaces && <span>{item.sharedReviewedRaces} shared content review(s)</span>}
        </button>)}
      </section>
      {!batch && !busy && batches.length > 0 && <p>Choose a county to begin or resume your review.</p>}
      {busy && !batch && <p role="status">Opening review task…</p>}
      {batch && <section aria-label={`${batch.county} review`}>
        <div className={styles.batchHeader}><div><h2>{batch.county}</h2>
          <p>{batch.election.name} · Revision {batch.revision}</p>
          <p>{batch.reviewedRaces} of {batch.raceCount} race contents reviewed · {batch.requiredReviewers} human review{batch.requiredReviewers === 1 ? "" : "s"} required</p>
          {!!batch.sharedReviewedRaces && <p>{batch.sharedReviewedRaces} reused from matching county entries. County source coverage is separate.</p>}
        </div><span className={styles.badge}>{batch.imported ? "Imported" : "Private draft"}</span></div>
        <p className={styles.scope}>This review checks names, offices and party labels against the certification.
          Ballot styles, local contests and geographic applicability are prepared separately.</p>
        <nav aria-label="Source pages" aria-describedby="page-navigation-help" className={styles.pages}>{pages.map(item =>
          <button key={item.sourcePage} disabled={busy} aria-current={page === item.sourcePage ? "page" : undefined}
            className={`${page === item.sourcePage ? "" : styles.secondary} ${item.complete ? styles.reviewedPageButton : ""}`}
            onClick={() => switchPage(item.sourcePage)}>Page {item.sourcePage}
            <span className={styles.pageStatus}>{item.pending ? "Unsaved choices" : item.complete ? "Content reviewed" :
              item.flagged ? "Needs attention" : `${item.reviewed}/${item.total} reviewed`}</span>
          </button>)}</nav>
        <p id="page-navigation-help" className={styles.small}>Reviewed pages are gray and skipped automatically.
          Opening one asks for confirmation. Shared content reviews count here; county source coverage is separate.</p>
        {hasPending && <p role="status" className={styles.pending}>You have {Object.keys(drafts).length} unsubmitted section decision(s).
          Choices stay here when changing pages; use Submit review to save them.</p>}
        <h3 ref={reviewHeading} tabIndex={-1} className={styles.reviewHeading}>{page ? `Review printed page ${page}` : "County review overview"}</h3>
        {!page ? <section className={styles.reviewOverview} aria-label="Review overview">
          <h4>{batch.imported ? "This county has already been imported" : "All page content is reviewed"}</h4>
          <p>{batch.imported ? "The saved review history remains available. Open a gray page above to inspect it." :
            "There are no unfinished content pages to open. You can inspect a reviewed page above or continue to county confirmation and import below."}</p>
          {batch.requiresCountyConfirmation && <p>Shared content approval does not check this county&apos;s contest list.
            Use the retained PDF to check county source coverage before confirming below.</p>}
          <a href={`${API}/batches/${batch.id}/source`} target="_blank" rel="noreferrer">Open retained PDF for county source coverage</a>
          {batch.imported && <p><a href="/editorial/preview">View imported records in the private guide preview</a></p>}
        </section> : <>
        {currentPage?.complete && <p className={styles.reviewedNotice}>This page&apos;s content is already reviewed.
          Viewing it does not reset any approval. You may still inspect the source or flag a correction.</p>}
        <div className={`${styles.comparison} ${currentPage?.complete ? styles.reviewedContent : ""}`}>
          <aside className={styles.evidence}>
            <h3>Official source · printed page {page}</h3>
            <p className={styles.small}>{pdfPage ? `PDF viewer page ${pdfPage}` : "Find the cited page manually in the PDF."}</p>
            <p><a href={sourceUrl} target="_blank" rel="noreferrer">Open retained PDF in a separate tab</a></p>
            <iframe key={sourceUrl} src={sourceUrl} title={`Official certification, printed page ${page}${pdfPage ? `, PDF page ${pdfPage}` : ""}`} />
            <p className={styles.small}>If your browser does not display PDFs, use the separate-tab link.
              Page buttons use the printed citation. Viewer links account for known cover-page offsets;
              check the printed page number when comparing facts.</p>
            <a href={batch.source.url} target="_blank" rel="noreferrer">Publisher&apos;s source</a>
          </aside>
          <form className={styles.facts} onSubmit={submitReview} onKeyDown={event => {
            // Enter in a transcription field must not submit the whole county.
            if (event.key === "Enter" && event.target instanceof HTMLInputElement && event.target.type === "text") event.preventDefault();
          }}>
            <h3>Extracted facts</h3>
            <p className={styles.small}>{batch.imported || !batch.current ? "This revision is read-only." :
              "Choose Accept or Flag for each section. Selecting Flag shows prefilled edit fields and a notes box. Save corrections first, then accept the corrected text. Submit everything together below."}</p>
            {visible.map(race => {
              const saved = race.decisions.find(item => item.reviewer === staff?.username);
              const draft = drafts[race.key];
              const choice = draft?.decision ?? saved?.decision;
              const edits = draft ? fieldCorrections(race, draft) : [];
              const editable = !batch.imported && batch.current && choice === "flagged";
              return <article key={race.key} className={styles.race} aria-label={race.ballotTitle}>
              <div className={styles.raceHeader}>
                {editable ? <div className={styles.officeTitle}>
                  <h4 className={styles.srOnly}>{race.ballotTitle}</h4>
                  <label htmlFor={`title-${race.key}`} className={styles.small}>Office title</label>
                  <input id={`title-${race.key}`} className={styles.transcriptionInput} maxLength={255} disabled={busy}
                    autoComplete="off" spellCheck={false} value={draft?.edits.ballotTitle ?? race.ballotTitle}
                    aria-describedby={edits.some(edit => edit.field === "ballotTitle") ? `original-title-${race.key}` : undefined}
                    onChange={event => editField(race, "ballotTitle", event.target.value)}
                    onBlur={event => editField(race, "ballotTitle", event.target.value.trim())} />
                  {edits.some(edit => edit.field === "ballotTitle") && <p id={`original-title-${race.key}`} className={styles.original}>Original: {race.ballotTitle}</p>}
                </div> : <h4>{race.ballotTitle}</h4>}
                <span className={styles.badge}>{race.reviewStatus === "reviewed" && race.sharedReviews?.length && !race.countySourceReviewed ? "Shared content reviewed" : statusLabel[race.reviewStatus]}</span>
              </div>
              <p className={styles.small}>{race.jurisdictionName}{race.districtLabel ? ` · ${race.districtLabel}` : ""}</p>
              <table className={editable ? `${styles.candidateTable} ${styles.editableCandidates}` : undefined}><caption className={styles.srOnly}>{race.ballotTitle} candidate labels</caption>
                <thead><tr><th>Candidate</th><th>Party</th></tr></thead>
                <tbody>{race.candidates.map((candidate, index) => <tr key={index}>
                  <td>{editable ? <>
                    <label className={styles.srOnly} htmlFor={`name-${race.key}-${index}`}>Candidate name {index + 1}</label>
                    <input id={`name-${race.key}-${index}`} className={styles.transcriptionInput} maxLength={255} disabled={busy}
                      autoComplete="off" spellCheck={false} value={draft?.edits[`ballotLabel:${index}`] ?? candidate.ballotLabel}
                      aria-describedby={edits.some(edit => edit.field === "ballotLabel" && edit.candidateIndex === index) ? `original-name-${race.key}-${index}` : undefined}
                      onChange={event => editField(race, `ballotLabel:${index}`, event.target.value)}
                      onBlur={event => editField(race, `ballotLabel:${index}`, event.target.value.trim())} />
                    {edits.some(edit => edit.field === "ballotLabel" && edit.candidateIndex === index) &&
                      <p id={`original-name-${race.key}-${index}`} className={styles.original}>Original: {candidate.ballotLabel}</p>}
                  </> : candidate.ballotLabel}</td>
                  <td>{editable ? <>
                    <label className={styles.srOnly} htmlFor={`party-${race.key}-${index}`}>Party {index + 1}</label>
                    <select id={`party-${race.key}-${index}`} className={styles.transcriptionInput} disabled={busy}
                      value={draft?.edits[`partyLabel:${index}`] ?? candidate.partyLabel}
                      aria-describedby={edits.some(edit => edit.field === "partyLabel" && edit.candidateIndex === index) ? `original-party-${race.key}-${index}` : undefined}
                      onChange={event => editField(race, `partyLabel:${index}`, event.target.value)}>
                      {["Republican", "Democratic", "Libertarian", "Green", "Independent", "None listed"].map(party => <option key={party}>{party}</option>)}
                    </select>
                    {edits.some(edit => edit.field === "partyLabel" && edit.candidateIndex === index) &&
                      <p id={`original-party-${race.key}-${index}`} className={styles.original}>Original: {candidate.partyLabel}</p>}
                  </> : candidate.partyLabel}</td>
                </tr>)}</tbody>
              </table>
              {!!race.matchingCounties?.length && <p className={styles.small}>Also listed in {race.matchingCounties.join(", ")}.</p>}
              {!!race.sharedReviews?.length && <div className={styles.sharedReview}>
                <strong>Human content review reused</strong>
                {race.sharedReviews.map(review => <p key={review.decisionId} className={styles.small}>
                  {review.reviewer} · {review.county} · {new Date(review.at).toLocaleString()} · {" "}
                  <a href={`${API}/batches/${review.batchId}/source${review.pdfPageNumber ? `#page=${review.pdfPageNumber}` : ""}`} target="_blank" rel="noreferrer">
                    Reviewed source page {review.sourcePage}
                  </a>
                </p>)}
                <p className={styles.small}>Matching office, district, names and parties do not need another acceptance.
                  This does not say this county&apos;s page, ordering, or any voter&apos;s ballot was checked.
                  You can still flag a problem below.</p>
              </div>}
              {race.sharedReviewBlockedReason && <p className={styles.scope}>{race.sharedReviewBlockedReason}</p>}
              {!batch.imported && <fieldset disabled={busy || !batch.current} className={styles.sectionDecision}>
                <legend>Decision for {race.ballotTitle}</legend>
                <div className={styles.choices}>
                  {(["accepted", "flagged"] as SectionChoice[]).map(value => <label key={value}>
                    <input type="radio" name={`decision-${race.key}`} value={value} checked={choice === value}
                      disabled={value === "accepted" && edits.length > 0}
                      onChange={() => changeDraft(race, { decision: value })} />
                    {value === "accepted" ? "Accept" : "Flag"}
                  </label>)}
                  {draft && <button type="button" className={styles.secondary} onClick={() => setDrafts(previous => {
                    const next = { ...previous }; delete next[race.key]; return next;
                  })}>Undo unsaved choices</button>}
                </div>
                {draft && <p className={styles.small}>Unsaved {draft.decision === "accepted" ? "acceptance" : "flag"}{edits.length ? ` · ${edits.length} field correction(s)` : ""}</p>}
                {choice === "flagged" && <div className={styles.flagDetails}>
                  <label htmlFor={`note-${race.key}`}>What is wrong in this section?</label>
                  <textarea id={`note-${race.key}`} rows={2} maxLength={2000} value={draft?.note ?? saved?.note ?? ""}
                    onChange={event => changeDraft(race, { decision: "flagged", note: event.target.value })} />
                  <p className={styles.small}>Add a note, or edit a transcription field above. If the official source itself is wrong,
                    describe the source issue here; do not silently rewrite its ballot label.</p>
                </div>}
              </fieldset>}
              {race.decisions.map(decision => <p className={styles.small} key={decision.reviewer}>
                Saved · {decision.reviewer}: {decision.decision === "accepted" ? "Accepted" : "Flagged"}
                {decision.carriedForward ? " (carried forward)" : ""}
                {decision.note ? ` — ${decision.note}` : ""}</p>)}
              {!!race.corrections?.length && <details className={styles.history}><summary>Correction history ({race.corrections.length})</summary>
                {race.corrections.map((correction, index) => <div key={index}>
                  <p className={styles.small}>{correction.reviewer} · {new Date(correction.at).toLocaleString()} · {correction.note}</p>
                  {correction.changes.map((change, index) => <p key={index} className={styles.small}>
                    {change.field === "ballotTitle" ? "Office title" : `Candidate ${(change.candidateIndex ?? 0) + 1} ${change.field === "ballotLabel" ? "name" : "party"}`}:
                    {" "}<del>{change.before}</del> → <ins>{change.after}</ins>
                  </p>)}
                </div>)}
              </details>}
            </article>})}
            {!batch.imported && <div className={styles.actions}>
              <p>{Object.keys(drafts).length} unsaved section decision(s) across this county.</p>
              <p className={styles.small}>By submitting, you confirm that accepted sections and proposed corrections match the cited source.
                Corrected sections stay flagged until accepted afterward. Untouched sections are not approved.</p>
              <button type="submit" disabled={!hasPending || busy || !batch.current}>{busy ? "Saving…" : "Submit review"}</button>
              {error && <p className={styles.error}>{error}</p>}
            </div>}
          </form>
        </div>
        </>}
        <footer className={styles.import}>
          {batch.requiresCountyConfirmation && !batch.imported && <label className={styles.countyConfirmation}>
            <input type="checkbox" checked={countyConfirmed} disabled={busy || hasPending || batch.reviewedRaces !== batch.raceCount}
              onChange={event => setCountyConfirmed(event.target.checked)} />
            <span>I checked that this county&apos;s listed contests appear on its cited source pages.
              Shared name and party reviews are reused; this does not confirm precinct or voter applicability.</span>
          </label>}
          {batch.countySourceConfirmedBy && <p>County source coverage confirmed by {batch.countySourceConfirmedBy} at import.</p>}
          <p>{batch.imported ? "This revision is now in the private civic records. It has not published a ballot." :
            "Submit your choices to save them. When every section is reviewed, import this county into the private civic records."}</p>
          {!batch.imported && <button disabled={busy || hasPending || !batch.current || batch.reviewedRaces !== batch.raceCount || (batch.requiresCountyConfirmation && !countyConfirmed)} onClick={importReviewed}>Import reviewed county</button>}
        </footer>
      </section>}
    </>}
  </main>;
}
