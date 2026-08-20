"use client";

import { FormEvent, useState } from "react";

type Citation = { authorityName: string; sourceUrl: string; checkedAt: string; sourceLabel: string };
type Support = { geographicAreaId: string; areaType: string; name: string; boundaryVersionId: string; explanation: string; source: Citation };
type Ballot = { ballotVersionId: string; label: string; electionName: string; electionDate: string; officialSource: Citation };
type PlausibleBallot = { ballot: Ballot; supportedBy: Support[]; explanation: string };
type Resolution = {
  status: string; message?: string; confidence?: number; addressPersisted: false;
  demonstration: boolean; reasonCodes: string[]; ballot?: Ballot; supportedBy?: Support[];
  plausibleBallots?: PlausibleBallot[];
};

function CitationView({ citation, demo }: { citation: Citation; demo: boolean }) {
  return (
    <p className="citation">
      <span>{demo ? "Synthetic source" : "Official source"}:</span>{" "}
      <a href={citation.sourceUrl} target="_blank" rel="noreferrer">{citation.sourceLabel}</a>
      {` · ${citation.authorityName} · checked ${new Date(citation.checkedAt).toLocaleDateString("en-US", { timeZone: "UTC" })}`}
    </p>
  );
}

function BallotCard({ ballot, support, demo }: { ballot: Ballot; support: Support[]; demo: boolean }) {
  return (
    <article className="ballot-card">
      <p className="result-label">Resolved ballot</p>
      <h2>{ballot.label}</h2>
      <p className="election-meta">
        {ballot.electionName} · {new Date(`${ballot.electionDate}T00:00:00Z`).toLocaleDateString("en-US", { dateStyle: "long", timeZone: "UTC" })}
      </p>
      <CitationView citation={ballot.officialSource} demo={demo} />
      <h3>Why this ballot matched</h3>
      <ul className="support-list">
        {support.map((item) => (
          <li key={item.boundaryVersionId}>
            <strong>{item.name}</strong>
            <span>{item.areaType.replaceAll("_", " ")}</span>
            <p>{item.explanation}</p>
            <CitationView citation={item.source} demo={demo} />
          </li>
        ))}
      </ul>
    </article>
  );
}

export default function Home() {
  const [address, setAddress] = useState("");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setResolution(null); setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
      const response = await fetch(`${baseUrl}/api/v1/ballots/resolve`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ address }),
      });
      if (!response.ok) throw new Error("The ballot service is temporarily unavailable.");
      setResolution((await response.json()) as Resolution);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally { setAddress(""); setLoading(false); }
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
            <input id="address" name="address" autoComplete="street-address" value={address}
              onChange={(event) => setAddress(event.target.value)} placeholder="123 Main St, Copperas Cove, TX"
              minLength={5} maxLength={300} required />
            <button type="submit" disabled={loading}>{loading ? "Checking…" : "Show my ballot"}</button>
          </div>
        </form>
        <p className="privacy">Your address is used only to find your ballot. We do not save it.</p>
      </section>

      {resolution && (
        <section className="results" aria-live="polite">
          {resolution.demonstration && (
            <div className="demo-banner" role="status"><strong>Synthetic demonstration</strong>
              <span>No real address, boundary, candidate, or official ballot data is shown.</span></div>
          )}
          {resolution.status === "resolved" && resolution.ballot && resolution.supportedBy ? (
            <BallotCard ballot={resolution.ballot} support={resolution.supportedBy} demo={resolution.demonstration} />
          ) : resolution.plausibleBallots?.length ? (
            <div><h2>More than one ballot may apply</h2><p>{resolution.message}</p>
              {resolution.plausibleBallots.map((item) => <BallotCard key={item.ballot.ballotVersionId}
                ballot={item.ballot} support={item.supportedBy} demo={resolution.demonstration} />)}</div>
          ) : <p className="notice" role="status">{resolution.message}</p>}
          <p className="privacy-confirmation">Address saved: no</p>
        </section>
      )}
      {error && <section className="results"><p className="notice error" role="alert">{error}</p></section>}

      <section className="principles" aria-label="Product commitments">
        <article><h2>Exact ballot</h2><p>Address-based, never ZIP-code guessing.</p></article>
        <article><h2>Evidence first</h2><p>Every factual claim links to its source.</p></article>
        <article><h2>Nonpartisan</h2><p>Information for voters, not endorsements.</p></article>
      </section>
    </main>
  );
}
