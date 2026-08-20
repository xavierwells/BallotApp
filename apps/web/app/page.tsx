"use client";

import { FormEvent, useState } from "react";

type Citation = { authorityName: string; sourceUrl: string; checkedAt: string; sourceLabel: string };
type Support = { geographicAreaId: string; areaType: string; name: string; boundaryVersionId: string; explanation: string; source: Citation };
type Ballot = { ballotVersionId: string; label: string; electionName: string; electionDate: string; officialSource: Citation };
type PlausibleBallot = { ballot: Ballot; supportedBy: Support[]; explanation: string };
type CoverageBasis = "residential_population_estimate" | "address_coverage_estimate" | "land_area_estimate" | "unavailable";
type BrowseMatch = { ballot: Ballot; geographicSupport: Support[]; relationship: "within" | "overlaps";
  rank: number; estimatedAreaSharePercent: number | null; coverageBasis: CoverageBasis;
  coverageSources: Citation[]; mostCommonAreaMatch: boolean; explanation: string };
type BrowseAreaMatch = { geographicAreaId: string; name: string; areaType: string; rank: number;
  estimatedAreaSharePercent: number; coverageBasis: CoverageBasis; coverageSources: Citation[];
  mostCommonAreaMatch: boolean; explanation: string };
type BrowseResponse = { status: string; areaType: "zip" | "city" | "county"; query: string; exactMatch: false;
  demonstration: boolean; message: string; matches: BrowseMatch[]; areaMatches: BrowseAreaMatch[] };
type Resolution = {
  status: string; message?: string; confidence?: number; addressPersisted: false;
  demonstration: boolean; reasonCodes: string[]; ballot?: Ballot; supportedBy?: Support[];
  plausibleBallots?: PlausibleBallot[]; officialContactLinks?: string[];
};

const reasonLabels: Record<string, string> = {
  low_geocode_confidence: "The address match was not precise enough.",
  no_boundary_match: "No verified boundary covered the resolved location.",
  near_boundary: "The location is on or very close to a boundary.",
  boundary_source_conflict: "Official boundary sources disagree.",
  ballot_style_conflict: "More than one official ballot style matches the available geography.",
  ballot_data_unavailable: "Required official ballot data is not available yet.",
};

const coverageBasisLabels: Record<CoverageBasis, string> = {
  residential_population_estimate: "estimated residential population",
  address_coverage_estimate: "estimated residential addresses",
  land_area_estimate: "estimated land area",
  unavailable: "deterministic ordering; no coverage estimate available",
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

function BallotCard({ ballot, support, demo, variant = "resolved", explanation, position, total, browseRanking }: {
  ballot: Ballot; support: Support[]; demo: boolean; variant?: "resolved" | "plausible" | "browse";
  explanation?: string; position?: number; total?: number; browseRanking?: BrowseMatch;
}) {
  const plausible = variant === "plausible";
  const browse = variant === "browse";
  return (
    <article className={`ballot-card${plausible ? " plausible-ballot" : ""}`}>
      {browse && browseRanking?.mostCommonAreaMatch && (
        <p className="most-common-badge">Most common area match</p>
      )}
      <p className="result-label">
        {plausible ? `Possible ballot ${position} of ${total}` : browse ? `Area match ${position} of ${total}` : "Resolved ballot"}
      </p>
      <h2>{ballot.label}</h2>
      <p className="election-meta">
        {ballot.electionName} · {new Date(`${ballot.electionDate}T00:00:00Z`).toLocaleDateString("en-US", { dateStyle: "long", timeZone: "UTC" })}
      </p>
      <CitationView citation={ballot.officialSource} demo={demo} />
      {browse && browseRanking && (
        <div className="coverage-summary">
          {browseRanking.estimatedAreaSharePercent !== null ? <>
            <strong>Approximately {browseRanking.estimatedAreaSharePercent}%</strong>
            {` of the selected area's ${coverageBasisLabels[browseRanking.coverageBasis]}.`}
          </> : <span>{coverageBasisLabels[browseRanking.coverageBasis]}.</span>}
          <p>This ordering describes the selected area; it does not identify a voter&apos;s ballot.</p>
          {browseRanking.coverageSources.map((citation) => <CitationView key={`${citation.sourceUrl}-${citation.sourceLabel}`}
            citation={citation} demo={demo} />)}
        </div>
      )}
      {(plausible || browse) && explanation && <p className="possibility-explanation">{explanation}</p>}
      <h3>{plausible ? "Geography supporting this possibility" : browse ? "Why this ballot appears in the area" : "Why this ballot matched"}</h3>
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

function BrowseResults({ result }: { result: BrowseResponse }) {
  if (result.status !== "available" || (result.matches.length === 0 && result.areaMatches.length === 0)) {
    return <p className="notice" role="status">{result.message}</p>;
  }
  return (
    <div className="comparison" aria-labelledby="browse-results-title">
      <header className="comparison-header browse-header">
        <p className="result-label">Area browsing — not an exact match</p>
        <h2 id="browse-results-title">{result.matches.length > 0 ? "Ballots" : "Geographic matches"} found around {result.query}</h2>
        <p>{result.message}</p>
        <p className="comparison-warning"><strong>These results do not identify your ballot.</strong>{" "}
          A ZIP code, city, or county can contain multiple precincts and districts.</p>
      </header>
      {result.areaMatches.length > 0 && <section className="area-match-list" aria-label="Ranked geographic area matches">
        {result.areaMatches.map((item) => <article className="area-match-card" key={item.geographicAreaId}>
          {item.mostCommonAreaMatch && <p className="most-common-badge">Most common area match</p>}
          <p className="result-label">Area match {item.rank} of {result.areaMatches.length}</p>
          <h3>{item.name}</h3>
          <p className="area-percentage"><strong>Approximately {item.estimatedAreaSharePercent}%</strong>{" "}
            of the selected area&apos;s {coverageBasisLabels[item.coverageBasis]}.</p>
          <p>{item.explanation}</p>
          {item.coverageSources.map((citation) => <CitationView key={`${citation.sourceUrl}-${citation.sourceLabel}`}
            citation={citation} demo={result.demonstration} />)}
          <p className="no-ballot-notice">No ballot has been selected from this area estimate.</p>
        </article>)}
      </section>}
      <div className="candidate-list">
        {result.matches.map((item, index) => <BallotCard key={item.ballot.ballotVersionId}
          ballot={item.ballot} support={item.geographicSupport} demo={result.demonstration} variant="browse"
          explanation={item.explanation} position={index + 1} total={result.matches.length} browseRanking={item} />)}
      </div>
    </div>
  );
}

function UnresolvedComparison({ resolution }: { resolution: Resolution }) {
  const ballots = resolution.plausibleBallots ?? [];
  return (
    <div className="comparison" aria-labelledby="comparison-title">
      <header className="comparison-header">
        <p className="result-label">Not an exact match</p>
        <h2 id="comparison-title">More than one ballot may apply</h2>
        <p>{resolution.message}</p>
        <p className="comparison-warning"><strong>We have not selected a ballot for you.</strong>{" "}
          Compare the geographic evidence below or confirm your ballot with an election official.</p>
        {resolution.confidence !== undefined && <p className="confidence">Resolution confidence: {resolution.confidence}%</p>}
        {resolution.reasonCodes.length > 0 && (
          <ul className="reason-list" aria-label="Reasons an exact match was not made">
            {resolution.reasonCodes.map((reason) => <li key={reason}>{reasonLabels[reason] ?? reason.replaceAll("_", " ")}</li>)}
          </ul>
        )}
      </header>
      <div className="candidate-list">
        {ballots.map((item, index) => <BallotCard key={item.ballot.ballotVersionId}
          ballot={item.ballot} support={item.supportedBy} demo={resolution.demonstration}
          variant="plausible" explanation={item.explanation} position={index + 1} total={ballots.length} />)}
      </div>
      {resolution.officialContactLinks && resolution.officialContactLinks.length > 0 && (
        <aside className="official-help"><h3>Confirm with an election official</h3><ul>
          {resolution.officialContactLinks.map((link) => <li key={link}><a href={link} target="_blank" rel="noreferrer">Official election information</a></li>)}
        </ul></aside>
      )}
    </div>
  );
}

export default function Home() {
  const [mode, setMode] = useState<"address" | "browse">("address");
  const [address, setAddress] = useState("");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [browseAreaType, setBrowseAreaType] = useState<"zip" | "city" | "county">("city");
  const [browseQuery, setBrowseQuery] = useState("");
  const [browseResult, setBrowseResult] = useState<BrowseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setResolution(null); setBrowseResult(null); setLoading(true);
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

  async function handleBrowse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setResolution(null); setBrowseResult(null); setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
      const parameters = new URLSearchParams({ areaType: browseAreaType, query: browseQuery });
      const response = await fetch(`${baseUrl}/api/v1/ballots/browse?${parameters}`);
      if (!response.ok) throw new Error("The ballot browsing service is temporarily unavailable.");
      setBrowseResult((await response.json()) as BrowseResponse);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Something went wrong.");
    } finally { setLoading(false); }
  }

  function handleUseLocation() {
    setError(null); setLocationError(null); setResolution(null); setBrowseResult(null);
    if (!("geolocation" in navigator)) {
      setLocationError("Location services are not available in this browser. Enter your registered home address instead.");
      return;
    }
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
        const response = await fetch(`${baseUrl}/api/v1/ballots/resolve-location`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            longitude: position.coords.longitude,
            latitude: position.coords.latitude,
            accuracyMeters: position.coords.accuracy,
          }),
        });
        if (!response.ok) throw new Error("The ballot service is temporarily unavailable.");
        setResolution((await response.json()) as Resolution);
      } catch (requestError) {
        setLocationError(requestError instanceof Error ? requestError.message : "Something went wrong.");
      } finally { setLocationLoading(false); }
    }, (geolocationError) => {
      const messages: Record<number, string> = {
        1: "Location permission was denied. Enter your registered home address instead.",
        2: "Your location is unavailable. Enter your registered home address instead.",
        3: "The location request timed out. Try again or enter your registered home address.",
      };
      setLocationError(messages[geolocationError.code] ?? "Your location could not be read. Enter your registered home address instead.");
      setLocationLoading(false);
    }, { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 });
  }

  function changeMode(nextMode: "address" | "browse") {
    setMode(nextMode); setError(null); setLocationError(null); setResolution(null); setBrowseResult(null);
  }

  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Copperas Cove pilot</p>
        <h1 id="page-title">What&apos;s on your ballot?</h1>
        <p className="intro">Every race. Every candidate. Every proposition. Explained and sourced.</p>
        <div className="mode-switch" role="group" aria-label="How to find ballots">
          <button type="button" className={mode === "address" ? "active" : "secondary"} aria-pressed={mode === "address"}
            onClick={() => changeMode("address")}>Use my address</button>
          <button type="button" className={mode === "browse" ? "active" : "secondary"} aria-pressed={mode === "browse"}
            onClick={() => changeMode("browse")}>Browse without an address</button>
        </div>
        {mode === "address" ? <>
          <form onSubmit={handleSubmit}>
            <label htmlFor="address">Enter your address</label>
            <div className="form-row">
              <input id="address" name="address" autoComplete="street-address" value={address}
                onChange={(event) => setAddress(event.target.value)} placeholder="123 Main St, Copperas Cove, TX"
                autoCapitalize="words" spellCheck={false} minLength={5} maxLength={300} required />
              <button type="submit" disabled={loading || locationLoading}>{loading ? "Checking…" : "Show my ballot"}</button>
            </div>
          </form>
          <p className="privacy">Your address is used only to find your ballot. We do not save it.</p>
          <div className="location-option">
            <span aria-hidden="true">or</span>
            <button type="button" className="location-button" onClick={handleUseLocation}
              disabled={loading || locationLoading} aria-describedby="location-warning">
              {locationLoading ? "Getting location…" : "Use my current location"}
            </button>
            <p id="location-warning" className="location-warning">
              Use this only if you are currently at your registered home address. Your location is used once and is not saved.
            </p>
            {locationError && <p className="location-error" role="alert">{locationError}</p>}
          </div>
        </> : <>
          <form onSubmit={handleBrowse}>
            <label htmlFor="browse-query">Browse ballots by area</label>
            <div className="form-row browse-row">
              <select aria-label="Area type" value={browseAreaType}
                onChange={(event) => setBrowseAreaType(event.target.value as "zip" | "city" | "county") }>
                <option value="zip">ZIP code</option><option value="city">City</option><option value="county">County</option>
              </select>
              <input id="browse-query" name="query" value={browseQuery} onChange={(event) => setBrowseQuery(event.target.value)}
                placeholder={browseAreaType === "zip" ? "76522" : browseAreaType === "city" ? "Copperas Cove" : "Coryell County"}
                minLength={1} maxLength={255} pattern={browseAreaType === "zip" ? "[0-9]{5}(-[0-9]{4})?" : undefined}
                title={browseAreaType === "zip" ? "Enter a 5-digit ZIP code or ZIP+4" : undefined} required />
              <button type="submit" disabled={loading}>{loading ? "Searching…" : "Browse ballots"}</button>
            </div>
          </form>
          <p className="privacy">Area browsing shows possible ballots. It cannot determine your exact ballot.</p>
        </>}
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
            <UnresolvedComparison resolution={resolution} />
          ) : <p className="notice" role="status">{resolution.message}</p>}
          <p className="privacy-confirmation">Address saved: no</p>
        </section>
      )}
      {browseResult && <section className="results" aria-live="polite">
        {browseResult.demonstration && <div className="demo-banner" role="status"><strong>Synthetic demonstration</strong>
          <span>No real ballot or geographic data is shown.</span></div>}
        <BrowseResults result={browseResult} />
      </section>}
      {error && <section className="results"><p className="notice error" role="alert">{error}</p></section>}

      <section className="principles" aria-label="Product commitments">
        <article><h2>Exact ballot</h2><p>Address-based, never ZIP-code guessing.</p></article>
        <article><h2>Evidence first</h2><p>Every factual claim links to its source.</p></article>
        <article><h2>Nonpartisan</h2><p>Information for voters, not endorsements.</p></article>
      </section>
    </main>
  );
}
