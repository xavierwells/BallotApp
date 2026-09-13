"use client";

import { useEffect, useRef, useState } from "react";
import { publicationAction } from "./publication-model";
import type { PublicationStatus } from "./publication-model";
import styles from "./preview.module.css";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/editorial`;

export default function PublicationPanel({ batchId, county, onSessionExpired, onChanged }: {
  batchId: string; county: string; onSessionExpired: () => void; onChanged: () => void;
}) {
  const [status, setStatus] = useState<PublicationStatus | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [reason, setReason] = useState("");
  const [reload, setReload] = useState(0);
  const expired = useRef(onSessionExpired);
  expired.current = onSessionExpired;
  const writing = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus(null); setConfirmed(false); setError("");
    fetch(`${API}/guide-preview/${encodeURIComponent(batchId)}/publication`, {
      credentials: "include", cache: "no-store", signal: controller.signal,
    }).then(async response => {
      if (controller.signal.aborted) return;
      if (response.status === 401) { expired.current(); return; }
      const value = await response.json();
      if (!response.ok) throw new Error(typeof value.detail === "string" ? value.detail : "Could not check publication readiness.");
      if (!controller.signal.aborted) setStatus(value);
    }).catch(cause => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Readiness check failed."); });
    return () => controller.abort();
  }, [batchId, reload]);

  async function change(action: "publish" | "withdraw") {
    if (!status || writing.current) return;
    const available = publicationAction(status, batchId);
    if (action === "publish" ? !available.canPublish || !confirmed : !available.canWithdraw || !reason.trim()) return;
    const prompt = action === "publish"
      ? `Make this reviewed ${county} certification guide publicly readable? It is not a complete or personal ballot. The retained PDF and staff details stay private.`
      : `Take the currently published ${county} guide offline? Its release and review history will be retained privately.`;
    if (!window.confirm(prompt)) return;
    writing.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const path = action === "publish" ? `/guide-preview/${encodeURIComponent(batchId)}/publish`
        : `/guide-releases/${encodeURIComponent(status.currentReleaseId!)}/withdraw`;
      const body = action === "publish"
        ? { confirmed: true, basisHash: status.basisHash, expectedEventId: status.currentEventId }
        : { confirmed: true, reason: reason.trim(), expectedEventId: status.currentEventId };
      const response = await fetch(API + path, { method: "POST", credentials: "include", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!alive.current) return;
      if (response.status === 401) { expired.current(); return; }
      const value = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof value.detail === "string" ? value.detail : "The change could not be confirmed. Refresh publication status before retrying.");
      setNotice(action === "publish" ? "County guide published. The public link is below." : "County guide withdrawn. Its history has not been deleted.");
      setReason(""); setReload(value => value + 1);
      onChanged();
    } catch (cause) {
      if (alive.current) {
        setError(cause instanceof Error ? cause.message : "The change could not be confirmed. Refresh status before retrying.");
        // A lost response may have committed. Never automatically repeat a write.
        setStatus(null); setConfirmed(false);
      }
    } finally { writing.current = false; if (alive.current) setBusy(false); }
  }

  const actions = status ? publicationAction(status, batchId) : null;
  return <section className={styles.source} aria-label="County guide publication">
    <h3>Publish this county guide</h3>
    <p className={styles.small}>Review and publication are separate. A new draft does not replace or hide the published version.
      Publishing releases names, offices and parties with source links—not a complete ballot or a public copy of the PDF.</p>
    {notice && <p role="status">{notice}</p>}
    {error && <p className={styles.error} role="alert">{error}</p>}
    {!status && !error && <p role="status">Checking saved evidence and publication status…</p>}
    {!status && error && <button disabled={busy} className={styles.secondary} onClick={() => setReload(value => value + 1)}>Refresh publication status</button>}
    {status && <>
      <p><strong>{status.state === "published" ? "A guide is published" : status.state === "withdrawn" ? "Guide is offline" : "Not published"}</strong>
        {status.state === "published" && status.currentReleaseId && <> · <a href={`/guides?release=${encodeURIComponent(status.currentReleaseId)}`} target="_blank" rel="noreferrer">Open public guide</a></>}</p>
      {!status.canPublish && <p>Only an account granted publishing access can release or withdraw a guide. Your review work is preserved.</p>}
      {status.blockers.map(item => <p key={item.code} className={styles.scope}>{item.message}</p>)}
      {actions?.canPublish && <>
        <label className={styles.confirmation}><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />
          I approve public release of these reviewed official facts with source attribution under the project&apos;s official-fact policy.</label>
        <button disabled={!confirmed || busy} onClick={() => change("publish")}>{busy ? "Saving…" : actions.label}</button>
      </>}
      {actions && !actions.canPublish && status.publishedBatchId === batchId && <p>This revision is already published. No repeat review or publication is needed.</p>}
      {actions?.canWithdraw && <details className={styles.withdraw}><summary>Take the published guide offline</summary>
        <label htmlFor={`withdraw-${batchId}`}>Private reason</label>
        <textarea id={`withdraw-${batchId}`} value={reason} maxLength={2000} disabled={busy} onChange={event => setReason(event.target.value)} />
        <button className={styles.secondary} disabled={busy || !reason.trim()} onClick={() => change("withdraw")}>Withdraw published guide</button>
      </details>}
    </>}
  </section>;
}
