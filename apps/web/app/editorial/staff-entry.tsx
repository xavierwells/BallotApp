"use client";

import { useEffect, useState } from "react";
import StaffLogin from "./staff-login";
import { publicPages, staffPages, STAFF_HOME, STAFF_LOGIN } from "./staff-navigation";
import styles from "./review.module.css";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
type Staff = { username: string; canPublish: boolean };

export default function StaffEntry({ loginOnly = false }: { loginOnly?: boolean }) {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStaff(null); setLoading(true); setError("");
    fetch(BASE + "/api/v1/editorial/me", { credentials: "include", cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (response.status === 401) return;
        if (!response.ok) throw new Error("Staff access could not be checked. Please retry.");
        const identity = await response.json();
        if (!controller.signal.aborted) {
          if (loginOnly) window.location.replace(STAFF_HOME);
          else setStaff(identity);
        }
      }).catch(() => { if (!controller.signal.aborted) setError("Staff access could not be checked. Check the API connection and retry."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    const hide = () => { controller.abort(); setStaff(null); setLoading(true); };
    const show = (event: PageTransitionEvent) => { if (event.persisted) setReload(value => value + 1); };
    window.addEventListener("pagehide", hide); window.addEventListener("pageshow", show);
    return () => { controller.abort(); window.removeEventListener("pagehide", hide); window.removeEventListener("pageshow", show); };
  }, [loginOnly, reload]);

  async function signOut() {
    setBusy(true); setError("");
    try {
      const response = await fetch(BASE + "/api/v1/editorial/logout", { method: "POST", credentials: "include", cache: "no-store" });
      if (!response.ok) throw new Error("Sign-out failed");
      setStaff(null); window.location.replace(STAFF_LOGIN);
    } catch { setError("Sign-out could not be confirmed. Please retry Sign out."); }
    finally { setBusy(false); }
  }

  return <main className={styles.workspace}>
    <header className={styles.header}><div><a href="/">← Homepage</a><h1>{loginOnly ? "Staff login" : "Staff site map"}</h1>
      <p>Review tools and public pages, all in one place.</p></div>
      {staff && <div className={styles.account}><span>Signed in as {staff.username}</span>
        <button className={styles.secondary} disabled={busy} onClick={signOut}>Sign out</button></div>}
    </header>
    {error && <p className={styles.error} role="alert">{error}</p>}
    {loading ? <p role="status">Checking staff access…</p> : !staff ? <>
      {error ? <button className={styles.secondary} onClick={() => setReload(value => value + 1)}>Retry access check</button> : <StaffLogin />}
    </> : <>
      <p className={styles.scope}>{staff.canPublish ? "Your account has publishing access." : "Your account can review. Publishing requires a separate grant."}
        {" "}Opening a page does not approve, import or publish anything.</p>
      <nav aria-label="Staff tools"><h2>Staff tools</h2><div className={styles.siteLinks}>
        {staffPages.map(page => <a key={page.href} href={page.href}><strong>{page.title}</strong><span>{page.description}</span></a>)}
      </div></nav>
      <nav aria-label="Public pages"><h2>Public pages</h2><div className={styles.siteLinks}>
        {publicPages.map(page => <a key={page.href} href={page.href}><strong>{page.title}</strong><span>{page.description}</span></a>)}
      </div></nav>
      <nav aria-label="API documentation"><h2>Developer references</h2><p>
        <a href={`${BASE}/docs`} target="_blank" rel="noreferrer">Swagger API explorer</a>{" · "}
        <a href={`${BASE}/redoc`} target="_blank" rel="noreferrer">API reference</a>{" · "}
        <a href={`${BASE}/openapi.json`} target="_blank" rel="noreferrer">OpenAPI specification</a>
      </p><p className={styles.small}>Documentation availability follows your deployment settings. Staff API actions still require authorization.</p></nav>
      <button className={styles.secondary} disabled={busy} onClick={() => setReload(value => value + 1)}>Refresh staff access</button>
    </>}
  </main>;
}
