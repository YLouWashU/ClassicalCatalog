import re
from spotipy import Spotify
from enrich.spotify_auth import get_spotify_client
from common.models import Recording, ComparisonRecording, SpotifyStatus


def _clean_query(text: str) -> str:
    """Remove catalog numbers, parenthetical notes, and excess whitespace."""
    text = re.sub(r"\b[A-Z]{2,}\d[\w\s-]*\b", "", text)   # catalog numbers
    text = re.sub(r"\([^)]*\)", "", text)                   # parentheticals
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_main_performer(performers: str) -> str:
    """Extract the primary performer name (before '/', ',', or 'Orchestra')."""
    # e.g. "Philadelphia Orchestra / Yannick Nézet-Séguin" -> "Nézet-Séguin"
    # Strip instrument annotations like "(piano)", "(violin)" before splitting
    performers = re.sub(r"\([^)]*\)", "", performers).strip()
    parts = re.split(r"[/,]", performers)
    # Prefer the conductor name (usually after /)
    if len(parts) > 1:
        return parts[-1].strip()
    return parts[0].strip()


def search_recording(
    composer: str,
    work: str,
    performers: str,
    sp: Spotify | None = None,
) -> tuple[str | None, str | None, SpotifyStatus]:
    """
    Search Spotify for a classical recording.
    Returns (album_url, album_image_url, status).
    """
    if sp is None:
        sp = get_spotify_client()

    work_clean = _clean_query(work)
    composer_clean = _clean_query(composer).split()[-1]  # use last name
    performer_clean = _extract_main_performer(performers)
    performer_parts = performer_clean.split()
    performer_last = performer_parts[-1] if performer_parts else ""

    # Strategy 1: composer + work + performer
    query = f"{composer_clean} {work_clean} {performer_last}"
    results = sp.search(q=query, type="album", limit=10)
    album = _pick_best_album(results, composer_clean, performer_last)
    if album:
        image_url = album["images"][0]["url"] if album.get("images") else None
        return album["external_urls"]["spotify"], image_url, SpotifyStatus.found

    # Strategy 2: composer + work only (broader)
    query2 = f"{composer_clean} {work_clean}"
    results2 = sp.search(q=query2, type="album", limit=20)
    album2 = _pick_best_album(results2, composer_clean, performer_last)
    if album2:
        image_url = album2["images"][0]["url"] if album2.get("images") else None
        return album2["external_urls"]["spotify"], image_url, SpotifyStatus.found

    return None, None, SpotifyStatus.not_found


def _pick_best_album(results: dict, composer_last: str, performer_last: str) -> dict | None:
    """
    Pick the best album from Spotify search results.
    Prefer albums where the artist name contains the performer's last name.
    """
    albums = results.get("albums", {}).get("items", [])
    composer_lower = composer_last.lower()
    performer_lower = performer_last.lower()

    # First pass: exact performer match in artist name
    for album in albums:
        artist_names = " ".join(a["name"].lower() for a in album["artists"])
        if performer_lower in artist_names:
            return album

    # Second pass: any album — return first result
    return albums[0] if albums else None


def enrich_recording(recording: Recording, sp: Spotify | None = None) -> Recording:
    """Add spotify_url, album_image_url and spotify_status to a recording in place."""
    url, image_url, status = search_recording(
        composer=recording.composer,
        work=recording.work,
        performers=recording.performers,
        sp=sp,
    )
    recording.spotify_url = url
    recording.album_image_url = image_url
    recording.spotify_status = status

    for comp in recording.comparison_recordings:
        comp_url, comp_image_url, comp_status = search_recording(
            composer=comp.composer,
            work=comp.work,
            performers=comp.performers,
            sp=sp,
        )
        comp.spotify_url = comp_url
        comp.album_image_url = comp_image_url
        comp.spotify_status = comp_status

    return recording
