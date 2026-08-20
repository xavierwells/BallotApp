# Coarse browse coverage source review

**Review date:** 2026-08-20  
**Pilot query:** ZIP/ZCTA 76522  
**Decision:** Census sources are approved candidates for a private, reproducible
pilot calculation after the operator records the source reviews. No percentage
is approved for publication until the calculation output and evidence are
reviewed.

**Import checkpoint:** The pinned calculation was successfully imported as
draft evidence on 2026-08-20: Coryell 38,975/41,123 (94.78%) and Lampasas
2,148/41,123 (5.22%). It remains excluded from non-demo public responses until
reviewed and promoted.

## Selected initial method

The first calculation will estimate what share of a selected browse area falls
in each county or other target using **2020 Census residential population**:

1. retrieve the 2020 ZCTA polygon from the Census TIGERweb current service;
2. retrieve the intersecting 2020 Census blocks from the Census 2020 service;
3. use each block's published `POP100` and county code;
4. sum population by target county and divide by the total population assigned
   to the selected ZCTA; and
5. retain the exact responses, checksums, query parameters, numerator,
   denominator, methodology version, and calculation time.

This uses no address, voter record, registration record, or individual-level
data. It is a 2020 population estimate, not a current USPS delivery-address
ratio and not a prediction of an individual voter's ballot.

## Sources and terms

| Role | Official source | Vintage | Use decision |
| --- | --- | --- | --- |
| Browse boundary | [Census TIGERweb 2020 ZCTA layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/2) | The current service identifies a January 1, 2025 service vintage; the layer itself is the 2020 Census ZCTA product. | No fee or account is required. Private retention of pinned responses is approved under the project owner's public-civic-data exception, subject to Census attribution and non-endorsement language. |
| Population and county assignment | [Census TIGERweb 2020 Census Blocks layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/10) | January 1, 2020 geography; fields include `STATE`, `COUNTY`, `GEOID`, and `POP100`. | Same decision. Use only aggregate published block population; do not attempt to identify households or individuals. |
| API conditions | [Census Data API terms of service](https://www.census.gov/data/developers/about/terms-of-service.html) | Checked 2026-08-20. | Display the required notice: “This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.” Do not imply Census endorsement or falsely represent modified content as Census content. Treat service limits as variable and use pinned, cacheable operator imports rather than request-time calls. |

## ZCTA limitation

Census describes ZCTAs as generalized areal representations of USPS ZIP Code
service areas. ZIP Codes are delivery routes, not electoral geography, and not
every valid ZIP has a ZCTA. The public interface must use “ZIP area” or “Census
ZCTA approximation,” retain all alternatives, and never claim that a ranked
result identifies the voter's address, county, precinct, or ballot.

## Deferred alternative

The HUD–USPS ZIP crosswalk offers residential-address ratios that may be more
current and closer to the product concept. Its site was WAF-gated during this
review, so access, retention, redistribution, attribution, and automation terms
could not be verified. It remains **held**, not rejected. If approved later,
its address-coverage estimate can coexist as a newer calculation basis without
overwriting the Census population estimate.

## Publication gate

A coverage estimate may be labeled “most common area match” only when:

- source artifacts and calculation evidence are retained;
- numerator, denominator, basis, vintage, and methodology are visible to the
  reviewer;
- ranks are complete and descending;
- the responsible geography/ballot evidence is independently valid; and
- the UI retains the no-exact-match warning and every alternative.

## Operator workflow

After migration `012_browse_area_coverage` is applied, synchronize the source
registry. One manifest-driven command records the operator's decision for both
Census inputs; the manifest carries the shared terms and each source's notes.
Replace `YOUR-OPERATOR-ID` with a stable non-PII operator reference.

```powershell
docker compose run --rm api python -m app.cli.bootstrap_authorities

docker compose run --rm api python -m app.cli.review_browse_sources `
  --manifest /app/data/browse/copperas-cove-pilot.json `
  --reviewer-reference YOUR-OPERATOR-ID
```

Validate the pinned requests and expected calculation without writing:

```powershell
docker compose run --rm api python -m app.cli.import_browse_coverage `
  --manifest /app/data/browse/copperas-cove-pilot.json
```

Expected calculation:

```text
Coryell County: 38975/41123 (94.78%)
Lampasas County: 2148/41123 (5.22%)
Validated pinned Census browse coverage calculation
```

After review, rerun with `--apply`. This creates draft rows only and is
idempotent. Promotion and public use remain a separate review step.
