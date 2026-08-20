# Copperas Cove pilot boundary-source review

**Review date:** 2026-08-20  
**Target election:** November 3, 2026  
**Current decision:** Private retention and transformation of public official
geometry is approved under the risk controls below. No current source is yet
approved by itself for authoritative November 2026 address resolution; several
are approved for reference import pending authority confirmation.

**Import checkpoint:** The checksum-pinned TLC 2026-primary reference was
successfully imported on 2026-08-20 as 98 draft boundaries: Bell 72, Coryell
16, and Lampasas 10. These rows remain excluded from public resolution.

## Why one map is not enough

An address may simultaneously belong to a county election precinct, city,
school district, congressional district, state legislative districts, and a
special district. A county precinct is a foundational election unit, but it
does not prove every local ballot-style membership. Exact resolution requires
either all applicable authoritative boundaries or an official ballot-style
crosswalk that accounts for splits.

The resolver must distinguish:

- an authority's own current boundary;
- a state/federal reference copy assembled from authority submissions;
- a map intended only for viewing; and
- a geometry file whose terms permit copying and processing.

## Source inventory and go/no-go result

| Geography | Best source found | Currency and authority | Terms/use finding | Resolution decision |
| --- | --- | --- | --- | --- |
| Bell County election precincts | [Bell County Elections precinct maps](https://www.bellcountytx.com/departments/elections/index.php), including county-owned ArcGIS maps | County Elections links the maps and is the responsible authority; page is current for the November 2026 election. | Direct viewing is allowed under the pilot policy. Feature-service export endpoint, completeness, and reuse terms are not yet verified. | **Hold import.** Use for manual comparison only. |
| Coryell County election precincts | [Coryell County 2023 voting map](https://coryellcountytax.com/wp-content/uploads/2023/11/2023-Coryell-Voting-map.pdf) linked by the current Elections page | Official county PDF; filename indicates 2023, while the Elections page is current for November 2026. | Direct viewing/manual check approved. No machine-readable geometry or explicit geometry reuse terms found. | **Hold import.** Ask the county for the current GIS layer or boundary descriptions and confirmation it applies to November 2026. |
| Lampasas County election precincts | [Voting-district map effective January 1, 2023](https://www.co.lampasas.tx.us/upload/page/6665/2023/lampasas_vtd_county_wide_jan_2023.pdf) | Official county map with an explicit effective date; current-election applicability has not been confirmed. | Direct viewing/manual check approved. No downloadable authoritative geometry or reuse terms found. | **Hold import.** Ask the Elections Office for current GIS geometry or legal descriptions and 2026 confirmation. |
| Statewide county precinct reference | [Texas Legislative Council 2026 primary precincts](https://data.capitol.texas.gov/dataset/precincts) | Updated July 15, 2026; council collects changes from county officials, but labels the collection as reference and directs users to county officials. It is for the 2026 primary, not yet the November general election. | Dataset is CC Attribution. `Precincts26P.zip` is pinned at SHA-256 `70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107`; its 9,614 polygons use EPSG:3081. | **Approved for private reference import only.** The Bell (72), Coryell (16), and Lampasas (10) slices remain draft. Never mark them verified for the November resolver without county confirmation or a 2026-general release. |
| Copperas Cove city limits | [City planning documents](https://www.copperascovetx.gov/DocumentCenter/View/1981/2020-Comprehensive-Plan-Update-Adopted-03-17-2020-PDF) and Census TIGERweb current legal boundaries | City document is from 2020. Census says its current release reflects legal boundaries reported through the 2025 Boundary and Annexation Survey. Neither establishes that no later annexation affects November 2026. | Direct review allowed. No current city-owned downloadable geometry with approved reuse terms found. | **Hold exact municipal use.** Census geometry could support coarse browse only after data-use approval; city confirmation remains required for exact ballot membership. |
| Copperas Cove ISD | [Texas Legislative Council 2025–2026 school districts](https://data.capitol.texas.gov/dataset/school-districts) | Updated March 25, 2026 from TEA and appraisal-district updates. TLC explicitly calls it reference data, not a legal boundary determination. | CC Attribution; importable only after a content-use/attribution approval. | **Reference candidate only.** Confirm against CCISD or the relevant appraisal districts before exact resolution. |
| Congressional, Texas House, Texas Senate, and SBOE districts | [Texas Legislative Council Capitol Data Portal](https://data.capitol.texas.gov/) | TLC identifies current plans and districts for 2026 elections and publishes shapefiles. | Portal datasets identify CC Attribution; exact selected plan resources and attribution must be recorded at import. | **Conditional go.** May be imported as verified only after the importer pins the enacted/current plan ID, checksum, effective election, and license notice. |
| County and broad place browsing | [Census TIGERweb current release](https://tigerweb.geo.census.gov/tigerwebmain/TIGERweb_main.html?eml=gd) | Census states the current release reflects 2026 BAS legal boundaries and January 1, 2025 school boundaries. | Public federal source; exact download and citation record still required. | **Conditional go for coarse browse.** Not a replacement for local election-authority evidence. |

## Import requirements

Before any candidate becomes a verified `boundary_version`, record:

1. exact downloadable resource URL and publisher;
2. dataset/plan/vintage identifier;
3. effective date or election applicability;
4. license, retention, transformation, redistribution, and attribution terms;
5. downloaded-file SHA-256 and normalized-geometry SHA-256;
6. coordinate reference system and transformation to SRID 4326;
7. geometry validity and coverage checks;
8. comparison with the responsible authority's current map/order;
9. reviewer and review time; and
10. any known gaps, splits, overlaps, or conflicts.

Draft/reference geometry must never be queried by the public resolver. An
overlap or disagreement is retained as a conflict and must not be silently
merged.

## Approved boundary-data exception

Approved by the project owner on 2026-08-20: BallotApp may download, normalize,
and privately retain official public boundary data to produce a working
resolver. Explicitly permitted datasets are preferred, but absent or incomplete
terms do not automatically block necessary public civic data.

Every import must retain the source link, publisher, retrieval time, original
and normalized checksums, known terms, attribution, and terms uncertainty. Do
not publicly redistribute original source files. Reference geometry remains
ineligible for public resolution until independently confirmed by the
responsible election authority or reconciled with an official ballot-style
crosswalk.

An explicit prohibition, restrictive license, access-control bypass, personal
data, publisher objection, or credible material legal/civil concern stops the
import and requires escalation. See [`GUARDRAILS.md`](GUARDRAILS.md).
