"use client";

import { FormEvent, useState } from "react";
import { STAFF_HOME } from "./staff-navigation";
import styles from "./review.module.css";

const API = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080"}/api/v1/editorial`;

export default function StaffLogin() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    const values = new FormData(event.currentTarget);
    const payload = { username: String(values.get("username") ?? ""), password: String(values.get("password") ?? "") };
    event.currentTarget.reset(); values.delete("password");
    try {
      const response = await fetch(API + "/login", { method: "POST", credentials: "include", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      payload.password = "";
      if (!response.ok) {
        if (response.status === 401) throw new Error("Sign-in failed. Check your username and passphrase.");
        if (response.status === 429) throw new Error("Too many sign-in attempts. Wait before trying again.");
        throw new Error("Could not sign in. Check the editorial service and try again.");
      }
      // Fixed internal destination: URL parameters cannot send credentials or
      // authenticated visitors to an arbitrary external return URL.
      window.location.replace(STAFF_HOME);
    } catch (reason) {
      setError(reason instanceof TypeError ? "Could not connect to the editorial service. Please retry." :
        reason instanceof Error ? reason.message : "Could not sign in.");
      setBusy(false);
    } finally { payload.password = ""; }
  }

  return <section className={styles.login}><h2>Staff sign-in</h2>
    <p>Use your existing editorial account. After signing in, you’ll see the staff site map.</p>
    <p>Visitors do not need an account to read published guides.</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <form onSubmit={signIn}>
      <label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" minLength={3} maxLength={80} required disabled={busy} />
      <label htmlFor="password">Passphrase</label><input id="password" name="password" type="password" autoComplete="current-password" maxLength={256} required disabled={busy} />
      <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    </form>
  </section>;
}
