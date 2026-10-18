"""AniList: every anime with all the names it goes by, how its seasons, films and specials connect,
and what's airing. It needs no key, and allows about 30 requests a minute; kura/web.py waits when
it says the minute's requests are spent.
"""

from kura.cache import DAY, Cache
from kura.core import catalog, fields
from kura.core.catalog import Anime
from kura.web import Send, Service, WebError, send

API = "https://graphql.anilist.co"

# Everything Kura reads about an entry (see kura/core/catalog.py), asked for in one go. A change
# to it changes SHAPE, so answers kept from before aren't read for the new fields.
_ENTRY = """
    id format episodes duration status
    startDate { year month day }
    endDate { year month day }
    title { romaji english native }
    synonyms
    description(asHtml: false)
    genres
    studios(isMain: true) { nodes { name } }
    coverImage { large extraLarge }
    bannerImage
    nextAiringEpisode { episode airingAt }
    relations {
      edges {
        relationType
        node { id type format startDate { year month day } title { romaji english } }
      }
    }
"""
_SEARCH = (
    "query ($search: String, $count: Int) {"
    f" Page(perPage: $count) {{ media(search: $search, type: ANIME) {{ {_ENTRY} }} }} }}"
)
_ONE = f"query ($id: Int) {{ Media(id: $id, type: ANIME) {{ {_ENTRY} }} }}"
SHAPE = 2  # which _ENTRY the answers kept were asked with


class AniList:
    def __init__(
        self, transport: Send = send, service: Service | None = None, cache: Cache | None = None
    ) -> None:
        self._service = service or Service("AniList", transport)
        self._cache = cache

    def search(self, text: str, count: int = 8) -> list[Anime]:
        """Entries whose names fit `text`, best first, as AniList ranks them. An answer is kept
        for a week, so a rescan doesn't ask again."""
        key = f"anilist search {SHAPE} {count} {text.casefold()}"
        answer = self._cache.get(key, 7 * DAY) if self._cache else None
        if answer is None:
            variables = {"search": text, "count": count}
            answer = self._service.json(
                "POST", API, payload={"query": _SEARCH, "variables": variables}
            )
            if self._cache:
                self._cache.put(key, answer)
        return catalog.anime_list(answer)

    def entry(self, anime_id: int, *, fresh: bool = False) -> Anime | None:
        """One entry by its AniList number, or None when AniList has no such entry. An answer
        is kept for a week; `fresh` asks again anyway (how far a show still airing has got)."""
        key = f"anilist entry {SHAPE} {anime_id}"
        answer = self._cache.get(key, 7 * DAY) if self._cache and not fresh else None
        if answer is None:
            payload = {"query": _ONE, "variables": {"id": anime_id}}
            try:
                answer = self._service.json("POST", API, payload=payload)
            except WebError as error:
                if error.status == 404:
                    return None
                raise
            if self._cache:
                self._cache.put(key, answer)
        media = fields.mapping(fields.mapping(answer, "data"), "Media")
        return catalog.anime(media) if media else None
