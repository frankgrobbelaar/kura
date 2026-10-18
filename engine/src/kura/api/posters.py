"""Choosing a title's poster (kura/posters.py): what there is to choose from, and the choice."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status

from kura import credentials, posters
from kura.api.common import AniListClient, ApiModel, Database, Paths, Web
from kura.artwork import poster_address
from kura.cache import Cache
from kura.care import Care
from kura.tmdb import Tmdb

router = APIRouter()


class PosterOption(ApiModel):
    poster: str  # what's kept: TMDB's image path, or AniList's cover address
    address: str  # where the picture is, to show it (GET /artwork?address=)
    source: Literal["tmdb", "anilist"]
    language: str | None  # "en", "ja"; None for one without words (or AniList's)
    width: int | None
    height: int | None


class PosterChoices(ApiModel):
    found: str | None  # the poster TMDB or AniList gave it
    chosen: str | None  # the owner's, when they chose one
    options: list[PosterOption]  # the one it has first
    problem: str | None  # why TMDB's or AniList's couldn't be asked for now


class Chosen(ApiModel):
    poster: str | None  # None: back to the one TMDB or AniList gave it


@router.get("/titles/{title_id}/posters")
def poster_choices(
    title_id: int, conn: Database, paths: Paths, web: Web, anilist: AniListClient
) -> PosterChoices:
    """The posters to choose from for a title: TMDB's (with the owner's key) and AniList's
    cover."""
    key = credentials.load(paths, "tmdb")
    tmdb = Tmdb(key, web, cache=Cache(paths.cache)) if key else None
    found = posters.choices(conn, title_id, tmdb, anilist)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kura has no such title.")
    return PosterChoices(
        found=found.found,
        chosen=found.chosen,
        options=[
            PosterOption(
                poster=each.poster,
                address=poster_address(each.poster) or "",
                source=each.source,
                language=each.language,
                width=each.width,
                height=each.height,
            )
            for each in found.options
        ],
        problem=found.problem,
    )


@router.put("/titles/{title_id}/poster", status_code=status.HTTP_204_NO_CONTENT)
def choose_poster(title_id: int, body: Chosen, conn: Database, request: Request) -> None:
    """Keeps the owner's choice of poster, or goes back to the one found. The poster next to the
    show follows, when the owner has those."""
    if not posters.choose(conn, title_id, body.poster):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That isn't a poster from TMDB or AniList."
        )
    care: Care = request.app.state.care
    care.wake()  # the poster next to the show, written anew
