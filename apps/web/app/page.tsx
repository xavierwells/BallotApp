"use client";

import { FormEvent, useState } from "react";

type Resolution = {
  status: string;
  message: string;
  addressPersisted: boolean;
};

export default function Home() {
  const [address, setAddress] = useState("");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResolution(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
      const response = await fetch(`${baseUrl}/api/v1/ballots/resolve-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });
      if (!response.ok) throw new Error("The ballot service is temporarily unavailable.");
      setResolution((await response.json()) as Resolution);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally {
      setAddress("");
    }
  }

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Copperas Cove pilot</p>
        <h1 id="page-title">What&apos;s on your ballot?</h1>
        <p className="intro">Every race. Every candidate. Every proposition. Explained and sourced.</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="address">Enter your address</label>
          <div className="form-row">
            <input
              id="address"
              name="address"
              autoComplete="street-address"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder="123 Main St, Copperas Cove, TX"
              minLength={5}
              maxLength={300}
              required
            />
            <button type="submit">Show my ballot</button>
          </div>
        </form>
        <p className="privacy">Your address is used only to find your ballot. We do not save it.</p>
        {resolution && <p className="notice" role="status">{resolution.message}</p>}
        {error && <p className="notice error" role="alert">{error}</p>}
      </section>
      <section className="principles" aria-label="Product commitments">
        <article><h2>Exact ballot</h2><p>Address-based, never ZIP-code guessing.</p></article>
        <article><h2>Evidence first</h2><p>Every factual claim links to its source.</p></article>
        <article><h2>Nonpartisan</h2><p>Information for voters, not endorsements.</p></article>
      </section>
    </main>
  );
}
