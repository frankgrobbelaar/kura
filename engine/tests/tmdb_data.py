"""TMDB's answers, built the way TMDB shapes them, for tests (there is no key in the repo).

Air dates run weekly from the first episode, across seasons, so a show's episodes keep their
order in time the way real ones do.
"""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from kura.core.fields import Json

ANIMATION = 16


def tv_details(
    show_id: int,
    name: str,
    seasons: Sequence[int],
    *,
    first_aired: date,
    specials: int = 0,
    status: str = "Ended",
    titles: Mapping[tuple[int, int], str] | None = None,
    special_dates: Sequence[date] = (),
    aired: Mapping[tuple[int, int], date] | None = None,
) -> dict[str, object]:
    """/tv/{id} with every season appended: `seasons` are the sizes of seasons 1, 2, …

    Episodes air weekly; `aired` sets an episode's date, and the weeks run on from there."""
    named = titles or {}
    dated = aired or {}
    answer: dict[str, object] = {
        "id": show_id,
        "name": name,
        "original_name": name,
        "first_air_date": first_aired.isoformat(),
        "status": status,
        "in_production": status == "Returning Series",
        "poster_path": f"/poster-{show_id}.jpg",
        "backdrop_path": f"/backdrop-{show_id}.jpg",
        "seasons": [
            {"season_number": number, "episode_count": size}
            for number, size in enumerate([specials, *seasons])
            if number > 0 or specials
        ],
    }
    day = first_aired
    for number, size in enumerate(seasons, start=1):
        episodes: list[Json] = []
        for episode in range(1, size + 1):
            day = dated.get((number, episode), day)
            episodes.append(_episode(show_id, number, episode, day, named.get((number, episode))))
            day += timedelta(days=7)
        answer[f"season/{number}"] = {"season_number": number, "episodes": episodes}
    if specials:
        days = list(special_dates) or [first_aired] * specials
        answer["season/0"] = {
            "season_number": 0,
            "episodes": [
                _episode(show_id, 0, n, days[min(n - 1, len(days) - 1)], named.get((0, n)))
                for n in range(1, specials + 1)
            ],
        }
    return answer


def movie_details(movie_id: int, title: str, released: date, minutes: int) -> dict[str, object]:
    return {
        "id": movie_id,
        "title": title,
        "original_title": title,
        "release_date": released.isoformat(),
        "runtime": minutes,
        "poster_path": f"/poster-movie-{movie_id}.jpg",
        "backdrop_path": f"/backdrop-movie-{movie_id}.jpg",
    }


def tv_search(*results: tuple[int, str, date | None]) -> dict[str, object]:
    """/search/tv: (id, name, first aired) of each Japanese animated show found."""
    return {
        "page": 1,
        "results": [
            {
                "id": show_id,
                "name": name,
                "original_name": name,
                "first_air_date": aired.isoformat() if aired else "",
                "genre_ids": [ANIMATION, 10759],
                "origin_country": ["JP"],
                "original_language": "ja",
                "popularity": 100.0 - index,
            }
            for index, (show_id, name, aired) in enumerate(results)
        ],
    }


def movie_search(*results: tuple[int, str, date | None]) -> dict[str, object]:
    return {
        "page": 1,
        "results": [
            {
                "id": movie_id,
                "title": title,
                "original_title": title,
                "release_date": released.isoformat() if released else "",
                "genre_ids": [ANIMATION],
                "original_language": "ja",
                "popularity": 50.0 - index,
            }
            for index, (movie_id, title, released) in enumerate(results)
        ],
    }


def _episode(show_id: int, season: int, number: int, aired: date, title: str | None) -> Json:
    return {
        "season_number": season,
        "episode_number": number,
        "name": title or f"Episode {number}",
        "air_date": aired.isoformat(),
        "runtime": 24,
        "still_path": f"/still-{show_id}-{season}-{number}.jpg",
    }


# Dragon Ball Z's seasons on TMDB, as the title board shows them: 291 episodes in nine seasons.
DBZ_SEASONS = (39, 35, 33, 32, 26, 29, 25, 34, 38)
