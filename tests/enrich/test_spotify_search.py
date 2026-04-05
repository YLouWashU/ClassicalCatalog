import pytest
from enrich.spotify_search import search_recording, _extract_main_performer, _clean_query
from common.models import SpotifyStatus


def test_extract_main_performer_with_slash():
    result = _extract_main_performer("Philadelphia Orchestra / Yannick Nézet-Séguin")
    assert result == "Yannick Nézet-Séguin"


def test_extract_main_performer_single():
    result = _extract_main_performer("Daniil Trifonov")
    assert result == "Daniil Trifonov"


def test_clean_query_removes_catalog_numbers():
    result = _clean_query("Die Kunst der Fuge BWV1080 DG 483 8530")
    assert "DG" not in result or "483" not in result


@pytest.mark.integration
def test_search_well_known_recording_finds_result():
    """Beethoven 5th by Karajan — should always be on Spotify."""
    url, status = search_recording(
        composer="Beethoven",
        work="Symphony No 5",
        performers="Berlin Philharmonic / Herbert von Karajan",
    )
    assert status == SpotifyStatus.found
    assert url and "open.spotify.com" in url


@pytest.mark.integration
def test_search_florence_price_symphony():
    url, status = search_recording(
        composer="Florence Price",
        work="Symphony No 1",
        performers="Philadelphia Orchestra / Yannick Nézet-Séguin",
    )
    # May or may not be on Spotify — just verify it returns a valid status
    assert status in (SpotifyStatus.found, SpotifyStatus.not_found)


@pytest.mark.integration
def test_search_nonexistent_returns_not_found():
    url, status = search_recording(
        composer="Xyzzy Composer",
        work="Symphony Zzzz",
        performers="Nobody Orchestra",
    )
    assert status == SpotifyStatus.not_found
    assert url is None
