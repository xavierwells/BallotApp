from app.ballot_browsing import SyntheticDemoBallotBrowser, UnavailableBallotBrowser
from app.schemas.ballot_resolution import BrowseAreaType


def test_unavailable_browser_never_claims_an_exact_match() -> None:
    result = UnavailableBallotBrowser().browse(BrowseAreaType.CITY, "Copperas Cove")

    assert result.status == "not_available"
    assert result.exact_match is False
    assert result.matches == []


def test_synthetic_browse_returns_multiple_unselected_area_matches() -> None:
    result = SyntheticDemoBallotBrowser().browse(BrowseAreaType.ZIP, "76522")

    assert result.status == "available"
    assert result.exact_match is False
    assert len(result.matches) == 2
    assert all(match.relationship == "overlaps" for match in result.matches)
    assert [match.rank for match in result.matches] == [1, 2]
    assert result.matches[0].most_common_area_match is True
    assert result.matches[0].estimated_area_share_percent == 95
    assert result.matches[0].coverage_basis == "residential_population_estimate"
    assert result.matches[0].coverage_sources
    assert result.matches[1].most_common_area_match is False
    assert all("address-level match was not attempted" in match.geographic_support[0].explanation for match in result.matches)
    assert "76522" not in {str(match.ballot.ballot_version_id) for match in result.matches}
