"""Files waiting for a match: the owner's choice, pinned, and "not anime"."""

import json
import sqlite3
import time
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from kura import credentials
from kura.anilist import API as ANILIST
from kura.anilist import AniList
from kura.api import create_app
from kura.config import DataPaths
from kura.web import Service
from tests.conftest import TOKEN
from tests.fake_web import Asked, FakeWeb, reply
from tests.services import SAVED, internet
from tests.shelf import identify, library

COWBOY_BEBOP = json.loads((SAVED / "cowboy-bebop.json").read_text(encoding="utf-8"))
SERIES = next(m for m in COWBOY_BEBOP["data"]["Page"]["media"] if m["id"] == 1)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "Anime"


@pytest.fixture
def waiting(paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb) -> FakeWeb:
    """Four [subs] episodes in Downloads that Kura couldn't name, as on the design's board."""
    library(conn, root, [f"Downloads/[subs] ep0{n} final.mkv" for n in (3, 4, 5, 6)])
    identify(paths, conn, internet())
    stood_in = internet()
    web.answers.update(stood_in.answers)
    return web


def test_the_files_kura_couldnt_name_wait_with_their_facts(client: TestClient, waiting: FakeWeb):
    found = client.get("/review").json()

    assert [f["episode"] for f in found] == [3, 4, 5, 6]
    first = found[0]
    assert (first["group"], first["kind"], first["height"], first["codec"]) == (
        "subs",
        "episode",
        540,
        "hevc",
    )
    assert first["audio"] == ["jpn"]
    assert len(first["alike"]) == 3  # the other [subs] files beside it


def test_searching_anilist_scores_its_entries_against_the_file(
    client: TestClient, waiting: FakeWeb
):
    [first, *_] = client.get("/review").json()

    found = client.get(f"/review/{first['id']}/search", params={"q": "Cowboy Bebop"}).json()

    assert found[0]["anilistId"] == 1
    assert found[0]["title"] == "Cowboy Bebop"
    assert 0 <= found[0]["confidence"] <= 100


def test_searches_wait_out_anilists_limit_with_the_rest_of_kura(
    paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb
):
    library(conn, root, ["Downloads/[subs] ep03 final.mkv"])
    identify(paths, conn, internet())
    waited: list[float] = []
    app = create_app(TOKEN, paths, transport=web)
    app.state.anilist = AniList(service=Service("AniList", web, sleep=waited.append))
    spent = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(time.time() + 30)}
    web.answers[f"POST {ANILIST}"] = reply({"data": {"Page": {"media": []}}}, headers=spent)
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with TestClient(app, base_url="http://127.0.0.1", headers=headers) as client:
        [first] = client.get("/review").json()
        for text in ("Trigun", "Trigun Stampede"):
            client.get(f"/review/{first['id']}/search", params={"q": text})

    assert len(waited) == 1  # the second waited for the minute's reset
    assert 0 < waited[0] <= 30


def test_the_owners_choice_places_the_files_and_sticks(
    client: TestClient, waiting: FakeWeb, paths: DataPaths, conn: sqlite3.Connection
):
    credentials.save(paths, "tmdb", "a-test-key")
    waiting.answers[f"POST {ANILIST}"] = lambda asked: _entry_or_search(asked)
    [first, *_] = client.get("/review").json()

    answer = client.post(
        f"/review/{first['id']}", json={"anilistId": 1, "kind": "episode", "also": first["alike"]}
    )

    assert answer.json()["placed"] == 4
    rows = conn.execute(
        "SELECT episode, season, matched, pinned FROM files ORDER BY episode"
    ).fetchall()
    assert [tuple(row) for row in rows] == [(n, 1, "sure", 1) for n in (3, 4, 5, 6)]
    assert client.get("/review").json() == []

    identify(paths, conn, internet())  # a rescan
    assert conn.execute("SELECT COUNT(*) FROM files WHERE pinned = 1").fetchone()[0] == 4


def test_a_choice_kura_cant_place_asks_which_episode(
    client: TestClient, paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Old DVDs/VTS_01_1.VOB"])
    identify(paths, conn, internet())
    web.answers.update(internet().answers)
    [found] = client.get("/review").json()

    answer = client.post(f"/review/{found['id']}", json={"anilistId": 813, "kind": "episode"})

    assert answer.status_code == 422
    assert answer.json()["detail"].startswith("Which episode is it?")
    assert len(client.get("/review").json()) == 1

    answer = client.post(
        f"/review/{found['id']}", json={"anilistId": 813, "kind": "episode", "episode": 150}
    )

    assert answer.json()["placed"] == 1
    row = conn.execute("SELECT season, episode, pinned FROM files").fetchone()
    assert tuple(row) == (5, 11, 1)


def test_a_titles_match_changes_for_all_its_files_at_once(
    client: TestClient, paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, [f"Cowboy Bebop/Cowboy Bebop - 0{n}.mkv" for n in (1, 2, 3)])
    identify(paths, conn, internet())
    web.answers.update(internet().answers)
    [bebop] = [row[0] for row in conn.execute("SELECT id FROM titles")]

    [first] = client.get("/review", params={"title": bebop}).json()
    answer = client.post(
        f"/review/{first['id']}", json={"anilistId": 813, "kind": "episode", "title": bebop}
    )

    assert (first["episode"], len(first["alike"]), first["guesses"][0]["title"]) == (
        1,
        2,
        "Cowboy Bebop",
    )
    assert (answer.json()["placed"], answer.json()["waiting"]) == (3, 0)
    moved_to = answer.json()["titleId"]
    rows = conn.execute("SELECT title_id, season, episode, pinned FROM files ORDER BY episode")
    assert [tuple(row) for row in rows] == [(moved_to, 1, n, 1) for n in (1, 2, 3)]
    assert client.get(f"/titles/{moved_to}").json()["name"] == "Dragon Ball Z"
    assert client.get("/review", params={"title": bebop}).json() == []


def test_not_anime_is_left_out_for_good(
    client: TestClient, waiting: FakeWeb, conn: sqlite3.Connection
):
    [first, *_] = client.get("/review").json()

    assert client.post(f"/review/{first['id']}/ignore").status_code == 204

    assert len(client.get("/review").json()) == 3
    row = conn.execute("SELECT matched, pinned FROM files WHERE id = ?", (first["id"],)).fetchone()
    assert tuple(row) == ("ignored", 1)


def test_not_anime_is_listed_and_can_wait_for_a_match_again(
    client: TestClient, waiting: FakeWeb, conn: sqlite3.Connection
):
    [first, *_] = client.get("/review").json()
    client.post(f"/review/{first['id']}/ignore")

    [listed] = client.get("/review/ignored").json()
    assert (listed["id"], listed["path"], listed["size"]) == (
        first["id"],
        first["path"],
        first["size"],
    )
    assert client.delete(f"/review/{first['id']}/ignore").status_code == 204

    assert client.get("/review/ignored").json() == []
    assert first["id"] in [f["id"] for f in client.get("/review").json()]
    row = conn.execute(
        "SELECT matched, pinned, identified_at FROM files WHERE id = ?", (first["id"],)
    ).fetchone()
    assert tuple(row) == ("none", 0, None)  # looked up afresh at the next scan


def test_searching_by_a_name_only_tmdb_knows_finds_it_through_tmdb(
    client: TestClient, waiting: FakeWeb, paths: DataPaths
):
    credentials.save(paths, "tmdb", "a-test-key")
    [first, *_] = client.get("/review").json()

    found = client.get(f"/review/{first['id']}/search", params={"q": "Bola de Dragon Z"}).json()

    assert found[0]["anilistId"] == 813
    assert found[0]["reasons"][0] == "TMDB knows it as Dragon Ball Z"


@pytest.fixture
def turtle(paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb) -> int:
    """The Red Turtle, which AniList doesn't list, waiting since a scan without a TMDB key."""
    library(conn, root, ["Movies/The Red Turtle (2016)/The Red Turtle (2016).mp4"], minutes=80)
    identify(paths, conn, internet())
    web.answers.update(internet().answers)
    credentials.save(paths, "tmdb", "a-test-key")
    return conn.execute("SELECT id FROM files").fetchone()[0]


@pytest.mark.parametrize(
    "name", ["the red turtle", "La Tortue rouge", "レッドタートル ある島の物語"]
)
def test_a_film_anilist_doesnt_list_is_found_on_tmdb_by_any_of_its_names(
    client: TestClient, turtle: int, name: str
):
    [found] = client.get(f"/review/{turtle}/search", params={"q": name}).json()

    assert (found["anilistId"], found["tmdbType"], found["tmdbId"]) == (None, "movie", 337703)
    assert (found["title"], found["kind"], found["year"]) == ("The Red Turtle", "movie", 2016)
    assert found["cover"] == "/poster-movie-337703.jpg"
    assert found["reasons"][0] == "Only TMDB knows it"
    assert found["confidence"] >= 75


def test_choosing_a_film_only_tmdb_knows_makes_it_a_title_of_tmdbs_alone(
    client: TestClient, turtle: int, paths: DataPaths, conn: sqlite3.Connection
):
    answer = client.post(
        f"/review/{turtle}", json={"tmdbType": "movie", "tmdbId": 337703, "kind": "movie"}
    )

    assert answer.json()["placed"] == 1
    row = conn.execute(
        """SELECT f.matched, f.pinned, f.anilist_id, t.tmdb_type, t.tmdb_id, t.anilist_id
           FROM files AS f JOIN titles AS t ON t.id = f.title_id"""
    ).fetchone()
    assert tuple(row) == ("sure", 1, None, "movie", 337703, None)
    shown = client.get(f"/titles/{answer.json()['titleId']}").json()
    assert (shown["name"], shown["kind"]) == ("The Red Turtle", "movie")

    identify(paths, conn, internet())  # a rescan
    row = conn.execute("SELECT pinned, title_id FROM files").fetchone()
    assert tuple(row) == (1, answer.json()["titleId"])


def test_a_choice_names_what_the_file_is(client: TestClient, turtle: int):
    answer = client.post(f"/review/{turtle}", json={"kind": "movie", "tmdbType": "movie"})

    assert answer.status_code == 422


def test_offline_a_choice_changes_nothing_and_says_so(
    client: TestClient, waiting: FakeWeb, conn: sqlite3.Connection
):
    [first, *_] = client.get("/review").json()
    waiting.offline = True

    answer = client.post(f"/review/{first['id']}", json={"anilistId": 1})

    assert answer.status_code == 503
    assert answer.json()["detail"].endswith("Nothing was changed; try again in a moment.")
    assert conn.execute("SELECT COUNT(*) FROM files WHERE pinned = 1").fetchone()[0] == 0


def _entry_or_search(asked: Asked) -> object:
    variables = cast("dict[str, object]", asked.payload["variables"])
    if variables.get("id") == 1:
        return {"data": {"Media": SERIES}}
    return COWBOY_BEBOP


def test_a_titles_specials_keep_their_kind_and_files_that_dont_fit_wait(
    client: TestClient, paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb
):
    credentials.save(paths, "tmdb", "a-test-key")
    names = ["Cowboy Bebop - SP02.mkv", "Cowboy Bebop - 01.mkv", "Cowboy Bebop - 02.mkv"]
    library(conn, root, [f"Bebop/{name}" for name in names])
    identify(paths, conn, internet())
    web.answers.update(internet().answers)
    bebop = conn.execute("SELECT title_id FROM files WHERE path LIKE '%- 01.mkv'").fetchone()[0]
    with conn:  # the special, placed by the owner earlier
        conn.execute(
            """UPDATE files SET title_id = ?, season = 0, episode = 2, matched = 'sure',
                      pinned = 1
               WHERE path LIKE '%SP02.mkv'""",
            (bebop,),
        )

    [first] = client.get("/review", params={"title": bebop}).json()
    answer = client.post(
        f"/review/{first['id']}", json={"anilistId": 813, "kind": "episode", "title": bebop}
    ).json()

    assert (first["kind"], first["episode"], len(first["alike"])) == ("episode", 1, 2)
    assert (answer["placed"], answer["waiting"]) == (2, 1)
    rows = conn.execute("SELECT path, title_id, season, episode, matched FROM files ORDER BY path")
    assert [(Path(row[0]).name, *tuple(row)[1:]) for row in rows] == [
        ("Cowboy Bebop - 01.mkv", answer["titleId"], 1, 1, "sure"),
        ("Cowboy Bebop - 02.mkv", answer["titleId"], 1, 2, "sure"),
        ("Cowboy Bebop - SP02.mkv", None, None, None, "unsure"),  # not a second episode 2
    ]
    [waiting] = client.get("/review").json()
    assert Path(waiting["path"]).name == "Cowboy Bebop - SP02.mkv"


def test_a_file_from_another_title_cant_change_this_ones_match(
    client: TestClient, paths: DataPaths, conn: sqlite3.Connection, root: Path, web: FakeWeb
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Bebop/Cowboy Bebop - 01.mkv", "DBZ/Dragon Ball Z - 001.mkv"])
    identify(paths, conn, internet())
    web.answers.update(internet().answers)
    [(bebop, _), (_, dbz_file)] = conn.execute(
        "SELECT title_id, id FROM files ORDER BY path"
    ).fetchall()

    answer = client.post(
        f"/review/{dbz_file}", json={"anilistId": 813, "kind": "episode", "title": bebop}
    )

    assert answer.status_code == 404
