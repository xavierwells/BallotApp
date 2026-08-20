# Copperas Cove pilot authority-scope audit

**Completed:** 2026-08-20  
**Scope:** initial launch; direct links and manual checks only.

This audit determines which election authorities belong in the initial pilot
registry. It does not create a geographic district, infer a voter’s ballot, or
grant rights to retain source content. A special-purpose body is added only
when official evidence establishes both its relevance to Copperas Cove and an
election requiring voter-facing coverage.

## Confirmed pilot authorities

The six registered authorities remain the complete initial scope:

| Authority | Official evidence reviewed | Result |
| --- | --- | --- |
| City of Copperas Cove | The City's [Election Information](https://www.copperascovetx.gov/188/Election-Information) page lists its November 3, 2026 General Election materials. | Retain as municipality. |
| Coryell County | The County [Elections page](https://coryellcountytax.com/Elections/) lists the November 3, 2026 General Election and Copperas Cove vote centers. | Retain as county authority. |
| Bell County | The County [Office of Elections Administration](https://www.bellcountytx.com/departments/elections/index.php) page lists 2026 General Election information. | Retain as county authority. |
| Lampasas County | The County [Elections Office page](https://www.co.lampasas.tx.us/page/lampasas.testpage2) lists November 3, 2026 General Election information. | Retain as county authority. |
| Copperas Cove ISD | The district's [Election 2026 page](https://www.ccisd.com/page/election-2026) identifies Board of Trustee positions open on November 3, 2026. | Retain as school-district authority. |
| Texas Secretary of State, Elections Division | The [Texas Elections site](https://www.sos.state.tx.us/elections/index.shtml) is the statewide election-information authority. | Retain as state authority. |

## Special-purpose bodies reviewed but not added

| Body | Evidence | Why it is not a 2026 pilot ballot authority now |
| --- | --- | --- |
| Central Texas College | Its official board records show a Board of Trustee election held on May 3, 2025, and the Coryell County elections archive also lists that 2025 election. | No official 2026 election order, notice, or ballot was found. A past election and service/tax relationship do not establish an applicable 2026 ballot. |
| Coryell Central Appraisal District | Its official records show board governance; a Central Texas College board agenda documents an entity vote for appraisal-district director appointments. | The reviewed evidence does not establish a direct voter election for Copperas Cove residents in 2026. Do not treat an appointive board process as a voter ballot contest. |
| Middle Trinity Groundwater Conservation District | Its official public-notice page lists 2026 meetings and permit hearings. | No official boundary evidence tying the district to the pilot and no 2026 election order or ballot was found. Do not add it based only on regional water-planning or tax-list references. |

## Recheck triggers

Create a draft `special_district` authority only when one of the following is
published by the body or its authorized election administrator:

1. A current election order, notice of election, candidate-filing notice, or
   official ballot identifying an election that includes Copperas Cove voters.
2. Boundary or service-area evidence, paired with an election record, showing
   the body covers a relevant part of the pilot geography.
3. A county joint-election notice that identifies both the special-purpose
   authority and its applicable precincts or ballot styles.

At that point, add the authority as `draft`, add its official source URL with
`direct_link_manual_check`, and retain the evidence as a link/citation only
until content rights are separately reviewed.

## Sources consulted

- [City of Copperas Cove Election Information](https://www.copperascovetx.gov/188/Election-Information)
- [Coryell County Elections](https://coryellcountytax.com/Elections/)
- [Bell County Office of Elections Administration](https://www.bellcountytx.com/departments/elections/index.php)
- [Lampasas County Elections Office](https://www.co.lampasas.tx.us/page/lampasas.testpage2)
- [Copperas Cove ISD Election 2026](https://www.ccisd.com/page/election-2026)
- [Texas Elections](https://www.sos.state.tx.us/elections/index.shtml)
- [Central Texas College board agenda](https://www.ctcd.edu/about-ctc/leadership/board-of-trustees/board-meeting-agendas/)
- [Coryell Central Appraisal District 2026 budget](https://coryellcad.org/wp-content/uploads/2025/11/2026-Budget.pdf)
- [Middle Trinity Groundwater Conservation District public notices](https://www.middletrinitygcd.org/public-notices)
