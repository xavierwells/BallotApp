"use client";

import { useEffect, useState } from "react";
import { checkedDirectoryItems, guideDirectoryHref, guideReleaseHref } from "./browse-links";
import type { GuideSummary } from "./guide-model";
import styles from "./guide-links.module.css";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/guides`;

export default function GuideLinks({ county }: { county?: string }) {
  const [items, setItems] = useState<GuideSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setItems([]); setLoading(true); setError("");
    const timeout = setTimeout(() => { controller.abort(); setError("The guide search took too long. Please retry."); setLoading(false); }, 15_000);
    const query = new URLSearchParams({ limit: "20", ...(county ? { county } : {}) });
    fetch(`${API}?${query}`, { credentials: "omit", cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("Guide list unavailable");
        const value = await response.json();
        const next = checkedDirectoryItems(value.items, county);
        if (!controller.signal.aborted) setItems(next);
      }).catch(cause => { if (!controller.signal.aborted) setError(cause instanceof Error && !(cause instanceof TypeError) ? cause.message : "Could not connect to the guide service."); })
      .finally(() => { clearTimeout(timeout); if (!controller.signal.aborted) setLoading(false); });
    const hide = () => { clearTimeout(timeout); controller.abort(); setItems([]); setLoading(true); };
    const show = (event: PageTransitionEvent) => { if (event.persisted) setReload(value => value + 1); };
    window.addEventListener("pagehide", hide); window.addEventListener("pageshow", show);
    return () => { clearTimeout(timeout); controller.abort(); window.removeEventListener("pagehide", hide); window.removeEventListener("pageshow", show); };
  }, [county, reload]);

  return <section className={styles.directory} aria-label={county ? `Published guides for ${county}` : "Choose a published county guide"}>
    <h3>{county ? "Read this county’s published guide" : "Choose a county guide — no address needed"}</h3>
    <p>Reviewed candidate names, offices and parties. County-wide information, not your exact or complete ballot.</p>
    {loading && <p role="status">Checking published guides…</p>}
    {error && <p role="status">Published guide availability could not be checked. {error}{" "}<button type="button" onClick={() => setReload(value => value + 1)}>Retry guides</button></p>}
    {!loading && !error && items.length === 0 && <p>No guide is currently published{county ? ` for ${county}` : " here"}. This does not mean there is no election.</p>}
    <ul className={styles.links}>{items.map(item => <li key={item.releaseId}>
      <a href={guideReleaseHref(item.releaseId)}>Read {item.county} guide</a>
      <span>{item.electionName} · {item.electionDate}</span>
    </li>)}</ul>
    <p><a href={guideDirectoryHref(county)}>{county ? "See published guides for this county" : "See all published county guides"}</a></p>
  </section>;
}
