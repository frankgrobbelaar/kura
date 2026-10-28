# Kura

Kura (蔵, "storehouse") is a personal Windows app for one person's anime library. It maps folders
in any layout, identifies every file, reports what is missing or broken, renames for Plex, and
converts the whole library to one standard, with AI upscaling for SD sources. It is the owner's
own tool: one user, one PC, never commercial, no sign-in. The code is shared under the MIT
licence: anyone may fork it, but the repo takes no contributions.

**Where it stands (2026-10-18):** design language chosen; repo, CI, installer and updater
pipeline set up, with semantic versions, a changelog and a downloads page. Built and tested end to
end: first-run setup with ffmpeg fetched from the list the installer shows; the scan (find, read
with ffprobe, identify on AniList and TMDB, check for gaps and write the reports); "Which anime is
this?"; the watcher; Home's shelf of franchises and series, a page per franchise and per title
(seasons, episode map, the gap analysis as a document, delete with put back); tidying up with
History's undo; converting with the queue (the AI model for SD, Anime4K for 720p, NVENC HEVC
10-bit, every result checked before it takes its original's place, nights only, full and
unplugged drives handled); Settings; nightly backups and restoring one; the quarantine cleared
out daily; the tray with "Start with Windows" and notifications; and the small-things board (a
file open in another app, a crash told on Home, a failed conversion's log and "Mark as broken",
offline, notes in the window, a name that's taken, not enough space, damaged records, the
overnight note); light mode, Paper, as Windows is or as chosen; History a week at a time and
cleared on asking or daily; the player inside Kura (small over the page and moved anywhere,
full screen and back); English subtitles made on the PC from a video's own sound (Whisper on
the graphics card, in the queue with the conversions), with each video's languages on its title's
page and Home; another copy's English sound and subtitles added to the copy Tidy up keeps; and
Kura on any PC (what each PC can do, tested in Setup and Settings › About, AMD's and Intel's
encoders, this PC's own times, the lighter way where a card is small or slow); search, the
title bar's and each long list's; and Kura 1.0's (What's next, 13): a video in full and its
folder from any list, what each title is about, watched and picked up where it stopped,
Continue watching and Coming up on Home, the overnight health check, ticks on a title's videos,
the library at a glance and a poster of the owner's choosing. Kura 0.1.0, the first release,
went out on 2026-10-12, and 1.0.0, the first meant for everyday use, on 2026-10-18;
CHANGELOG.md has every release since. Since 1.0, details open as a card with a picture from the
episode (What's next, 14). Everything in [What's next](#whats-next) is built.

## Ground rules

- **One branch.** Work on `main` in `C:\GitHub\kura`. No feature branches, worktrees or PRs unless
  the owner asks. Commit and push to `main` once every check passes. If another session is working
  at the same time, stage only your own files (never `git add -A`).
- **Never change the Cinema look unasked.** Colours, type, shapes and motion come from the design
  canvas and live in [app/src/styles/tokens.css](app/src/styles/tokens.css). The owner: "do not
  change the color or anything".
- **Nothing changes until the owner reviews it.** Renames, moves, deletions and conversions are
  proposed first, applied only when approved, logged, and undoable. Duplicates and replaced
  originals go to quarantine (30 days), never straight to deletion; the one exception is the
  owner's own choice to delete converted files' originals once each result is checked and in
  place (2026-10-13). Anime files are never touched by uninstalling.
- **Kura is personal.** No email address, no company name (no employer, no organisation behind
  Kura) and no personal details beyond the owner's name (LICENSE, commit author), anywhere in
  the project: files, test data, commit messages, publisher, accounts, signing. The publisher
  name is "Kura". Commits carry only the owner's GitHub no-reply address (the clone's
  `user.email`), and Claude's co-author line has no address.
- **Only ship what Kura may share.** Kura is MIT. A dependency's licence must be on the allowed
  list in [engine/tools/third_party_notices.py](engine/tools/third_party_notices.py) (the
  installer build stops otherwise); code adapted from elsewhere keeps its notice (shadcn/ui:
  `app/src/components/ui/LICENSE-shadcn.txt`); no anime, artwork or other media in the repo or the
  installer, and titles appear only as example data. Pictures of Kura that go public (the
  README's, in `docs/readme/`), examples in the app and the design boards (with their snapshots
  in `docs/design/`) show made-up titles only, never a real series (the owner, 2026-10-14 and
  2026-10-15). The one exception is TMDB's logo, which its
  terms ask for beside its credit line (the owner, 2026-10-12; `app/src/assets/README.md`).
  Microsoft's redistributable files the AI model needs (its C++ runtime, and DirectML inside ONNX
  Runtime) aren't open source but are Microsoft's to let programs carry: the notices list them
  apart, under Microsoft's terms.
- **Every change you'd notice goes in CHANGELOG.md**, in the same commit, under "Unreleased"
  (see [docs/releasing.md](docs/releasing.md)). Versions are semantic, and every release must be
  newer than the last so installed copies see it as an update.
- **Latest versions.** Use the newest stable release of every package, tool and AI model, and keep
  them current wherever possible (the owner, 2026-10-15: "all packages, and AI models are on the
  latest where possible"; see "Updating dependencies" in
  [docs/development.md](docs/development.md)). A model or a downloaded tool moves up once the newer
  one measures at least as good and fast enough on the owner's PC, and never raises what a PC
  needs (the owner: "if users download this, and try with different spec pcs, they won't be able
  to use the models"): a heavier one comes as a choice beside the lighter one, as Best beside Fast.
- **Fix what you find.** A real fault found while working is fixed in the same piece of work, test
  first. Ask only about what is genuinely the owner's call: scope, money, anything irreversible or
  public.
- **Scoping means talking.** When the owner asks "is it possible…" or is scoping, answer in the
  conversation: no code, scripts or long checks.
- **Simple beats clever.** The bar is Revolut or Linear: few elements, one clear primary action,
  plain language, motion that explains. Code follows the same bar: small modules, obvious names.

## Layout

```
AGENTS.md       the guide for coding agents; each area below has its own AGENTS.md
CHANGELOG.md    every change you'd notice, by version
LICENSE         MIT
app/            the desktop app
  src/            React UI (TypeScript): components/, features/, lib/, styles/
  src-tauri/      Tauri shell (Rust): window, engine process, updates, installer config
engine/         the engine (Python): src/kura/, tests/, tools/ (build tools), kura-engine.spec,
                openapi.json
docs/           how it all works; docs/design/ holds the screens
scripts/        release.mjs (versions, notes, the downloads page), design-snapshot.mjs
.github/        CI and release workflows
```

## Commands

Run the app (Vite, the Rust shell, and the engine from source):

```powershell
cd app; pnpm tauri dev
```

Check everything CI checks (each line from the repo root):

```powershell
cd engine; uv run ruff format --check; uv run ruff check; uv run pyright; uv run pytest
cd app; pnpm check; pnpm build
cd app/src-tauri; cargo fmt --check; cargo clippy --all-targets -- -D warnings; cargo test
node --test "scripts/*.test.mjs"
cd app; pnpm build:engine; pnpm build:notices
```

Fix formatting: `uv run ruff format` (engine), `pnpm fix` (app), `cargo fmt` (shell).
Build the installer locally: `cd app; pnpm build:installer` (needs the signing key, see
[docs/releasing.md](docs/releasing.md)). Release: on GitHub, Actions › Release › Run workflow on
`main` (patch, minor, major or an exact version); from a PC,
`node scripts/release.mjs patch|minor|major` (commits and tags), then
`git push --atomic origin main v1.2.3`. A release reaches every installed copy, so releasing is
the owner's call.

## How it fits together

- **Shell** (`app/src-tauri`, Tauri 2, Rust): the window with its own title bar, one instance only.
  It starts the engine with a fresh token, tells the UI where it is, stops it on exit, and installs
  updates. Keep it thin.
- **UI** (`app/src`, React 19, Tailwind 4): talks to the engine over HTTP on 127.0.0.1 with the
  token. Server data goes through TanStack Query; screens live in `features/`.
- **Engine** (`engine/`, Python 3.14): everything else. A FastAPI app (`kura serve`) and a CLI
  (`kura export`, …), bundled by PyInstaller as a folder with its own Python. Library logic goes in
  `kura/core` as pure functions with no I/O; the code around it does files, network and database.
- **Data**: one SQLite file, `%LOCALAPPDATA%\Kura\kura.db`, upgraded by append-only migrations in
  `kura/migrations.py`. Development uses `engine/.dev-data` instead, never the real folder.
- **Contracts**: the engine's API is snapshotted in `engine/openapi.json` (a test fails when it
  drifts); the UI's types in `app/src/lib/engine.tsx` mirror it by hand. Change both together.

Details: [docs/architecture.md](docs/architecture.md).

## Decisions

Everything decided so far. Don't ask again; change only with the owner.

**The product**
- Point Kura at folders in any layout: one anime per folder, franchise sub-folders, or many anime
  mixed in one folder. Files live on local drives; the library is many episodes across many anime.
- It analyses every file, identifies it from free sources (TMDB and AniList) with artwork,
  reports gaps and health (a Markdown report per anime), renames for Plex, quarantines duplicates,
  and converts everything to one standard with a preview and estimates.
- Conversion history is kept "last modified" style. Installer, auto-updater, and an uninstaller that
  offers an export first.
- The pilot library is the whole Dragon Ball franchise (on the PC since 2026-10-12).
- Plex naming. Watched mostly on the PC; Plex or a phone maybe later.
- Kura's words never name Plex (the owner, 2026-10-11): the files keep the layout media servers
  read, but the app calls it "clean names" and says what it does, not who reads it. The naming
  choice is "Clean names" or "Keep my names". The release notes and the downloads page don't
  name it either (the owner, 2026-10-12), and they list every commit's title, so commit titles
  don't. Nor do the README and the design boards (2026-10-15): they say "media server apps".
- No piracy, in any form, and no copyright or content law broken (the owner, 2026-10-14: "We
  must enforce that we do not support any form of piracy"). Kura looks after video already on
  the PC and plays it only in its own window: it never searches for, downloads or shares video,
  never streams it over the internet, and never gets around copy protection. Nor does it
  download sound tracks or subtitle files (the owner asked for English ones, 2026-10-15: dubs
  have no lawful source apart from their releases, and subtitle sites are mostly unlicensed):
  English comes from the owner's own files instead (What's next, 11). The README ("Your
  own videos only"), the downloads page and Settings › About say so: it's for videos you have
  the right to keep and watch. The README is the tour, option B of three (the owner,
  2026-10-14; [docs/design/readme.html](docs/design/readme.html)), in six steps since English
  subtitles joined it, its pictures Kura's own screens with made-up titles, taken again when
  the screens they show change (the owner, 2026-10-15: "if need be we will also need to update
  the README images with the screen changes"). It markets Kura as the anime companion to a media
  server (the owner, 2026-10-15: "an additional tool to be used alongside tools like Plex,
  Jellyfin, etc", named only as "popular media server applications or something"): Kura gets
  the library right, the media server plays it. "The AI inside" names every AI model Kura uses,
  with its licence (the owner, 2026-10-15: "make sure to name any AI model we are using for any
  upscaling, etc"), so a model Kura takes on joins it in the same commit.
- Home shows the library (the owner, 2026-10-12): what this copy of Kura is up to (the engine,
  the data folder, the database, TMDB, updates) is in Settings › About. Its videos by picture
  are a summary at the top, and Scan again and Add a folder sit by the page's title with when
  the latest scan ran and what it found new or gone (the owner, 2026-10-13).
- Picture: crisp and clean; 720p or 1080p are both fine. **Every** file goes to the library standard,
  even 720p to 720p; a file already exactly at the standard is only renamed.
- The standard is chosen on Convert as in Settings, the estimates following at once (the owner,
  2026-10-13: "what if we want to convert later on to a different format?"). Changed, whatever
  isn't at the new one can be converted to it, Kura's own conversions too: from the converted
  file, or from its original if the owner puts that back from History first.
- Converted files' originals (the owner, 2026-10-13): kept in quarantine like any copy (the
  default), or deleted once each result is checked and in place, chosen on Convert and in
  Settings › Your data. A deleted original can't be put back, and History says so.
- Everything ends up neatly filed (the owner, 2026-10-11): seasons, specials and OVAs (Season 00)
  under their show, and every movie in a folder of its own, even one that arrived as a bare file.
  File and folder names match and stay clean and simple, nothing but the title, year, numbers and
  episode title: `TV\Show (Year)\Season 01\Show (Year) - S01E01 - Title.mkv` and
  `Movies\Title (Year)\Title (Year).mkv`, never release groups, resolutions or codecs. Folders a
  tidy-up leaves empty are removed (and come back on undo), and subtitle files beside a video move
  and rename with it.
- Only the page scrolls (the owner, 2026-10-11): the nav rail and the page's top (its title, or
  its breadcrumb) stay where they are, and so does a page's own section list beside it. A list
  that can run long inside a panel, as the queue's failed files, keeps to a height and scrolls in
  its place (the owner, 2026-10-14).
- The nav rail's tiles carry badges, as the boards show (the owner, 2026-10-13: "the little
  orange count badge is not showing over the convert side icon"): Convert, tinted, how far the
  file converting now has got, or how many files wait; Tidy up, solid amber, how many changes
  and files to match wait for the owner. Home, History and Settings have nothing that runs long
  enough to need one.
- The gap analysis shows in the app as a reader sees it, as an editor's Markdown preview would,
  under the title "Gap Analysis" (the owner, 2026-10-11).
- Deleting from Kura (the owner, 2026-10-11): a whole title, a season or one video, from the
  title's page, after Kura asks; and a file waiting for a match, or one set aside as not anime
  (listed there to match after all), from "Which anime is this?" (2026-10-13). It goes to
  quarantine like any copy set aside, never straight to deletion, and History (or the page,
  right after) puts it back until the clear-out.
- The queue works on several files at once (the owner, 2026-10-13: "batch selection to do
  certain actions like remove from queue", "we should be able to cancel all"): ticked files, or
  a whole season or title, go next, to the end or out of the queue together, and "Cancel all"
  empties it and stops the file converting, after asking. Files themselves never change.
- Not enough space (the owner, 2026-10-12): when a drive hasn't room for what's queued, the
  queue pauses and says what the files there need. The owner can empty that drive's quarantine
  first (with a second "are you sure": what's set aside there is deleted for good, before its
  days are up) or convert the files that fit now, the rest waiting for room. Kura doesn't write
  results to another drive. The Convert screen asks the same before queueing a choice that
  doesn't fit.
- History (the owner, 2026-10-14): a week's worth of days at a time with "Show older", a busy
  day's first 20 entries till "Show all", an undo on the day it was made. "Clear History" keeps
  the last 24 hours, 7 or 30 days, or nothing, after asking; Settings › Your data can have it
  cleared each day of what's older than 7, 30 or 90 days ("Forever", the default). Clearing
  forgets records only: files never change, and what still has a copy in quarantine stays, so
  it can be put back.
- Lists sort by release date by default, oldest first, on every page that lists series, movies,
  OVAs or specials, and can sort by name and other orders (the owner, 2026-10-11). They're
  grouped by type (the owner, 2026-10-13: "we need to order by type"): series first, then
  movies, OVAs and specials, each group in the order chosen; Home's shelf puts franchises first.
  "Recently added" and "Most missing" list every type together.
- A franchise's page shows what the library is missing of the whole franchise (the owner,
  2026-10-13): "Missing titles", beside the sort after a divider, puts in among its titles the
  series, films, OVAs and specials AniList ties to it by story that the library has no part of,
  each in its place as a dotted placeholder (the owner, 2026-10-13: "it should be a dotted
  placeholder for it in the library"), AniList's cover dimmed in it, with a hollow "Not in
  library" ("Coming" for one not out yet). One the library holds some of (a season TMDB keeps
  under a show it has, a special in a show's specials) isn't missing. A title's page has
  "Missing titles" too, leading to its franchise's page with them in, a title alone in the
  library included. Kura looks franchises up in the background, a few entries at a time,
  what the library lacks first, and asks about each again weekly, daily while it airs or is
  still to come, so a new one ("now there is a new Dragon Ball Super: Beerus out") appears by
  itself. Which titles make a franchise on Home doesn't change with what's looked up: only the
  links of entries the library holds tie titles together, as before.
- Everything says what it is (the owner, 2026-10-11): TV series, movie, OVA or special, as a word
  on its card, title page, review and report (status keeps the shapes), with counts by kind
  ("TV · 26 episodes · 2 OVAs · 1 movie"). Specials and OVAs are listed apart from missing
  episodes, so they never count as missing.
- "A simple tool, but we don't want to struggle with small things": empty, error and recovery
  states are designed, not afterthoughts (see the "small things" screen).
- A player inside Kura (the owner, 2026-10-14: "mostly just for quick checks, but could be
  watching"; "inside Kura's window, with the ability to go full screen or back to pip"): Play on
  a video opens a small player that floats over the page, always in sight however far you
  scroll, and can be dragged anywhere in the window, like YouTube's ("we shouldn't have to
  scroll down to see it"); it stays while you move between pages, goes full screen and comes
  back. It plays in Kura's own window: the engine makes the file what the window plays as it
  plays (H.264 by encoders that come with their licence: Windows' own first, which on the
  owner's PC starts in about a second and keeps up even while the AI model has the graphics card,
  then the cards'; never OpenH264, whose patent licence covers only Cisco's own builds; any sound
  as stereo AAC; the subtitles drawn into the picture), with nothing new to download. Text
  subtitles in the file join a moment after the picture: they're copied out of the file first,
  which reads all of it. The sound and subtitles picked last start the next video too. Built to
  the Kura Player canvas (What's next, 10).
- English subtitles made on the PC (the owner approved the canvas, 2026-10-15: "All happy go for
  it"). "Make English subtitles" on a title's videos, or Home's card for the videos with no
  English, takes a season, the title or everything without English (those with English subtitles
  too, when ticked), the sound to translate from (Japanese first), Best (Whisper medium, 1.53 GB)
  or Fast (Whisper small, 486 MB) and when (now, nights, after the queue). A model downloads the
  first time its quality is asked for, never in Setup. They share the queue with the conversions,
  one at a time on the card. They go beside the video as `.en.srt`, or `.kura.en.srt` when another
  file has that name, and are Kura's while they're as it wrote them (one the owner edits is
  theirs). History lists each batch with "Take them away" (to quarantine, put back from History);
  the player says "made by Kura" and that names and jokes can be off. English sound is written
  down, not translated. See docs/stack/speech.md.
- English from another copy (the same canvas, 2026-10-15): when Tidy up keeps one of two copies
  of an episode and the other has English sound or subtitles in it that the kept one hasn't (in
  it or beside it), the copies panel asks "Keep the better picture, with the other's English"
  (the default) or "Keep the better one as it is". With the English, the other copy stays where
  it is till a job next in the queue has lined the two up by a sound both have (Japanese first;
  copies sharing none aren't offered it), added the English to the kept copy, checked it and put
  it in place; then the kept copy as it was and the other go to quarantine together, as one
  change History puts back, kept there even when converted originals are deleted. Copies that
  aren't the same cut stay as they are; the next time, Tidy up says why and has "as it is" chosen.
- Kura on any PC (the owner, 2026-10-15: "if users download this, and try with different spec
  pcs, they won't be able to use the models, based on their specs"; "No need for my approval, go
  ahead make the designs"): Setup's last step (Tools and this PC) and Settings › About say what
  this PC can do, each part tested there with ffmpeg and ONNX Runtime: converting (the HEVC 10-bit
  encoder found: NVIDIA's NVENC, AMD's AMF or Intel's Quick Sync), the AI model, Anime4K, English
  subtitles (Best wants a card with 4 GB of its own memory, Fast 2 GB, else the processor) and the
  player. Times are measured on this PC (a test of about a minute, then every job), never the
  owner's card's; before then they say they're a guess. A part the PC can't do says so and what
  still works; one that's slow there (the AI model over 3 hours an episode) has the lighter way
  chosen first, the heavier one still a choice. The README and the downloads page say what a PC
  needs. Drawn on the Kura on Any PC canvas (What's next, 12). Built 2026-10-15
  (docs/stack/hardware.md): DirectML takes the PC's high-performance card and never quietly falls
  back to the processor for the AI model; Whisper on the processor loads one optimisation level
  below the highest (ONNX Runtime 1.24 breaks its half-precision layer norms there); a test only
  checks while a job has the card; new cards are timed anew, a new driver only checked.
- A title's videos come a season at a time (the owner, 2026-10-15: "The list of episodes for a
  series is too long again, not by season and a lengthy scroll. Do something nice for movies,
  series, etc"): a pill per season above the list, then Specials, then any files without a
  season; the season's list keeps to a height and scrolls in its place. Each video shows its
  episode's code and title, picture, length and size, its path on hover; a season's name under
  Seasons leads to its videos. A film, or any title that's one video, has Play at the top.
- Search (the owner, 2026-10-15: "We need some search capability below", "Anywhere else a
  search will be useful"): the title bar's search, as the boards draw it (without Ctrl K), finds
  the library's anime by any name they go by, their episodes by code or name and its videos by
  their files' names, and opens one on its page; an episode or video opens its title's videos
  searched for it. Every list that grows long has its own: Home's shelf, a franchise's titles, a
  title's videos through every season, Convert's What, the queue's Up next, Tidy up's changes,
  and History's filter by anime or file (the board's). Each narrows as you type, every word
  wanted however a name is written, and what it hides isn't acted on.
- Kura 1.0 (the owner, 2026-10-18: "Lets build 1 to 8, update or make any nice UI/UX changes and
  lets get to 1.0.0"; "I will be AFK, do the work, review, test, ec and get us to 1.0.0"), the
  eight from a list Claude offered:
  - Wherever a video is listed (a title's videos, the queue, "Which anime is this?", Tidy up's
    changes and copies), its ⋮ menu has "Show in folder" and "Copy path"; deleting moved into it
    as "Delete…", last and apart. A title's videos and episodes open in full (as a card since
    2026-10-19, below): the episode's title and air date, what happens in it (hidden till asked:
    it gives the story away), the file's tracks, length, size, place and what converting it does. An episode the
    library lacks opens from the episode map (a list the arrow keys go along) or the missing list,
    one still to come saying "Not out yet".
  - A title's page has About: TMDB's synopsis first (written for English readers), AniList's
    genres and main studio first, when it aired, where it stands (finished, still airing, not out
    yet, cancelled, on a break), how long an episode lasts, and its pages on AniList and TMDB. A
    franchise's page says what its lead is about and the years it spans; a title it lacks opens
    with what AniList knows of it.
  - Watched (Kura's records only: nothing is written into the files): the player tells the engine
    where a video is every ten seconds once it has played ten, a video seen to its last tenth is
    watched, and Play picks one stopped part way up there (not in its first 30 seconds), with
    "Start over" for a moment. A title's videos tick off what's watched and say what's left of
    one stopped; their menus mark them watched or not. Home's "Continue watching" lists each
    title part way through, latest first: the video stopped, or the next not yet watched, in the
    order a title's page plays them; a quick look leaves it as it was; "Remove from Continue
    watching" leaves a title out till it plays again.
  - Home's "Coming up": each of the library's shows with an episode still to come that it hasn't
    got, its next one by the day it airs, from the episode lists Kura keeps. On the day one airs
    the owner is told once (one notification for the day's). It never searches for or fetches an
    episode: what to do about one is the owner's own business.
  - The health check: from 23:00 to 07:00, while the queue has no job, a few at a time, every
    video is played a few seconds at three points, and again a month on. It played when its
    pictures came (counted with ffmpeg's `-progress`), as an original can print decoder noise
    starting at a point and still play well. A file that changes is due again, one Kura converts
    counts as checked, and a folder whose drive isn't connected waits. What didn't play is listed
    on Home ("See which"), to play and see, try again, call fine ("It plays fine") or mark as
    broken, one notification telling of the night's: nothing changes till the owner says. On
    unless turned off in Settings › Libraries, with "Check them all again".
  - Ticks on a title's videos, a whole season at once: marked watched or not together, deleted
    together once asked, or taken to Convert or to making English subtitles, where they start
    chosen (`?files=`).
  - Home's "At a glance", after the videos by picture and by language: how long the library plays
    end to end, how much was watched, what converting saved or used (each video's latest
    conversion still in place), and the three titles taking the most room.
  - A title's poster opens "Choose a poster": TMDB's (English, Japanese or without words) and
    AniList's largest cover. The choice is kept apart from the poster an episode list brings, so a
    refresh never undoes it; every screen and the poster next to the show follow it.
- Details as a card with its picture (the owner, 2026-10-19: "I am not liking this sidepanel",
  then "Go with B - A card with its picture", of three drawn on the
  [Kura Detail Options](https://claude.ai/artifact/6rp1m1fFNX5SmEKhDhgt7F) canvas beside A, a peek
  beside what was clicked, and C, the page opening up in place): what told more of one thing in a
  sheet at the window's side opens in a card over the page instead, the page dimming behind it.
  A video's or episode's has a picture from the episode across its top (TMDB's still, else a
  frame from the video, else its show's wide picture; the featured blue and its orb when there's
  none), Play on it (from where it stopped), its title on the picture for an episode the library
  lacks, what happens in it behind a blur of its words' shapes till asked, and the video or
  episode before and after it at its foot, in the page's order. A picture from the episode
  (TMDB's or a frame) stays blurred till asked ("Show the picture") while the episode isn't
  watched (the owner, 2026-10-19: "yes, blur unwatched episodes' pictures till asked"); the
  show's own picture isn't blurred, and a film shows its own picture before a frame. A title a
  franchise lacks shows its cover blurred across the top and beside its name; choosing a poster
  and the videos that didn't play are cards with a header. A card takes the focus as it opens,
  not its cross.
- Order of work: design language (done), repo and pipelines (done), then building.

**Design: Cinema** (the owner's pick of three; tokens in `app/src/styles/tokens.css`)
- Dark first: window #0b0c0f, glass panels white at 4% with 8% borders, text #f4f5f7 and #a3a8b3.
- One amber accent #f2b33d (text on it #1d1300, amber text #ffd27a). Featured panel blue #13254f
  with an orange orb #f08a24.
- Manrope for words, Geist Mono for paths, sizes and times. Pill buttons; panels 16 to 24 px round.
- Status by shape first: ready solid amber, converting pulsing, to convert solid blue #4f73b3,
  broken hatched, missing hollow.
- Motion: 120 ms hover and press, 200 ms toggles, 320 ms panels, 600 to 900 ms charts, one curve
  `cubic-bezier(.2,.8,.2,1)`, and none at all when Windows' animation effects are off.
- Shortcuts: Space pauses the queue and 1 to 3 picks a guess on "Which anime is this?"; no others
  (no Ctrl K search, arrows through posters or Ctrl Z undo: the owner, 2026-10-14, "Dont worry
  about the shortcuts"). Everything still works from the keyboard.
- Light mode is Paper (the owner's pick of three, 2026-10-14): a warm paper ground #f3efe6,
  cream panels #fffcf6 with #e6dfd1 borders and a soft warm shadow, text #1d1912 and #5d564a,
  amber text #7f5200, to convert #5b7cc4, the same amber and the same blue featured panel with
  its orb. On paper a ready square gets a darker edge, as solid amber is faint on cream. Each
  colour token holds both values (`light-dark()`), and a part that stays dark (the featured
  panel, a video) carries `scheme-dark`.
- Light or dark (2026-10-14, proposed with the options and let stand): as Windows is, changing
  when it does (the default), or always one: "Same as Windows", "Light" or "Dark" in Settings ›
  General. The shell keeps the choice and makes the window in it, so the page is right from its
  first frame.
- Canvases: [Kura Workflows](https://claude.ai/artifact/XgGkfpW6doBUPcnrPqrbxb) (13 boards, the source
  of truth for screens), the [options record](https://claude.ai/artifact/NWe6abnPRYCn6BGTVK25za),
  [Kura Light Mode Options](https://claude.ai/artifact/7Bdz7CoKjBbV8JrSLXfu4y) (Paper's Home
  and queue, the same in Cinema's dark beside them, and the two lights not chosen),
  [Kura Player](https://claude.ai/artifact/3MK2zSwv9fS1jzt2rP7Qw3),
  [Kura English Subtitles](https://claude.ai/artifact/RmbcFdZiDMXYvz69cQ9CYA) (seven boards) and
  [Kura on Any PC](https://claude.ai/artifact/BRYamJpre3pLDT4ZZtPhaN) (seven boards), and
  [Kura 1.0](https://claude.ai/artifact/7WBdCUmEhNuGVqpdpa3BKZ) (its screens as built, from the
  tests, with made-up titles), and
  [Kura Detail Options](https://claude.ai/artifact/6rp1m1fFNX5SmEKhDhgt7F) (the side sheet as it
  was and three ways instead, B, a card with its picture, chosen).
  Snapshots in [docs/design/](docs/design/), each canvas's as it changes (the owner, 2026-10-15:
  "Make sure to add the designs to the docs").

**Architecture**
- Tauri 2 shell, React + Tailwind + shadcn/ui (restyled to Cinema) UI, Python engine sidecar built
  with PyInstaller as a folder (fast start; ships its own Python). Local API with a per-launch token,
  plus a CLI. SQLite for data.
- A pure core behind small interfaces: parse → match → plan → check → estimate.
- Identification: anitopy parses names (chosen over guessit and aniparse after testing them on
  real names, see docs/stack/anitopy.md), AniList's search matches titles (a name that finds
  nothing is asked again in shorter forms, with a series' initials written out, and as AniList
  writes it, docs/stack/anilist.md; what AniList still can't find is searched on TMDB, which
  knows more languages and spellings, and AniList is asked for TMDB's names for it,
  docs/stack/tmdb.md; built 2026-10-13 at the owner's word), results map to TMDB IDs, low
  confidence goes to a review screen, and manual fixes are pinned so a rescan never undoes
  them. A series' special its show's list doesn't name is looked up by its own name, as an OVA
  or special of its own. An animated show or film AniList doesn't list at all (The Red Turtle,
  a Studio Ghibli co-production: the owner, 2026-10-28, "Not able to find it with either of
  these names") is TMDB's alone, a title with no AniList entry, taken without asking only when
  the files' year is its year; AniList's namesake of a TMDB find comes first. The manami
  offline database was the first plan, but its repository was archived in 2026 and stopped
  updating, so AniList's search, which is always current and needs no download, took its place
  (2026-10-11).
- Metadata from TMDB and AniList together, for full coverage (the owner, 2026-10-11). TMDB gives
  the episode lists (titles, air dates, Plex's seasons) and the artwork, with the owner's own key:
  Kura asks for it in Setup and Settings and keeps it on the PC, never in the code or an export.
  AniList, which needs no key, covers what TMDB lacks: obscure titles, how series, movies and
  specials connect, and airing dates. Missing episodes are those TMDB lists as aired that the
  library doesn't hold.
- When the missing-episode check runs (the owner, 2026-10-11): "Scan now" refreshes everything.
  While Kura is open it watches the library folders, so new and removed files are noticed at once
  (a scan starts five seconds after a folder goes quiet, and every screen catches up when it
  ends; the owner, 2026-10-13: "a single file removed ... picked up no changes"), and it catches
  up at start on what changed while it was closed. Every scan says what it found new and gone.
  Episode lists of shows still airing are refreshed every hour, finished shows' every week. A
  "Start with Windows" setting (off by default) keeps Kura in the tray so the checks carry on and
  it can notify; no scheduled task.
  Closing the window quits Kura unless "Keep Kura running when you close the window", a setting
  of its own under it, is on (the owner, 2026-10-12).
- Conversion is Kura's own pipeline: ffmpeg decodes (deinterlacing detected with idet), Python runs
  the AI model with ONNX Runtime on DirectML, ffmpeg resizes and encodes HEVC 10-bit on the card's
  own encoder (NVENC; AMF or Quick Sync on other PCs, whichever the PC check finds). Kura's
  own final mux handles the audio policy, subtitles, fonts, chapters and a "processed" tag. Every
  output is verified (length, streams, a test play) before it replaces the original, which goes
  to quarantine for 30 days.
- Upscaling by source, the owner's pick after the test on 2026-10-11:
  - SD (480p, 576p): Real-ESRGAN's anime video model (`realesr-animevideov3`, BSD-3-Clause) as
    ONNX in full precision: about an hour per episode on the GTX 1660 Super.
  - 720p: Anime4K's high-quality mode A through ffmpeg's libplacebo: about 10 minutes.
  - 1080p: no upscaling; re-encoded only when it isn't HEVC 10-bit already (about 3 minutes),
    otherwise just renamed. Anything bigger comes down to 1080p.
  - DirectML, not CUDA: CUDA was no faster and adds more than a gigabyte to download, and half
    precision is slower on GTX 16 cards. Real-ESRGAN's bigger anime model ran at 0.6 frames a
    second, far too slow. ONNX Runtime, the model (2.5 MB) and the shaders (0.4 MB) ship inside
    Kura; the measured speeds are the defaults in `engine/src/kura/core/estimate.py`.
- Speech (2026-10-15, docs/stack/speech.md): Whisper as onnx-community's half-precision ONNX
  exports on DirectML, its decoder's caches kept on the card with I/O binding (through NumPy a 6 GB
  card ran out of memory); pyannote's segmentation model 3.0 (6 MB, MIT, inside Kura) finds who
  speaks, as Silero's detector heard nothing under the action scenes' music; its stretches go to
  Whisper in windows of at most 30 s of the sound as it is. Measured on the GTX 1660 Super with a
  21-minute episode: Best 474 s, Fast 179 s, both hearing 96 to 97% of the release's lines.

**Data**
- `%LOCALAPPDATA%\Kura`: kura.db, artwork cache, nightly backups (keep 7), logs (30 days), and
  `tools\` (ffmpeg, downloaded on first run; see docs/stack/ffmpeg.md). The folder can be moved to
  another drive.
- Next to the files: `Kura - Gap analysis.md` and `Kura - History.md` per anime (Plex ignores .md),
  a tag inside every converted MKV, optional poster and fanart for media servers (built: off
  unless the owner turns it on), and the English subtitles Kura made when asked (`.en.srt`).
- Export: one zip (SQLite, JSON, CSV, the .md reports, settings). Today it holds the database,
  settings, every file change (`changes.csv`) and a manifest; it grows with the schema.
- Kura deletes only its own files, whatever its records say (a damaged database, or one an
  imported export held): what's in a day's folder of a quarantine, its unfinished copies
  (`.kura-converting`, `.kura-partial`) and its own `poster.jpg` and `fanart.jpg`; and,
  finishing a move to another drive that a stop cut short, the original once the same file is
  in place.
- Records damaged past use (the owner, 2026-10-12): as the engine starts, Kura says so and
  offers the newest backup that opens (with none, new records, as on its first day), keeping the
  damaged file beside them as it is, never deleting it.
- Uninstall: offer the export first, keep the data folder unless the owner ticks "Delete the
  application data", never touch anime files.

**Tooling** (2026-10-10, all latest stable)
- Python 3.14 (uv-managed), uv, Ruff, Pyright (strict), pytest, FastAPI, Typer, PyInstaller.
- Node LTS, pnpm 12, Vite 8, React 19, TypeScript 7, Tailwind 4, Vitest 5, Biome 2 (lint and
  format). TypeScript 7 is the native compiler; typescript-eslint and openapi-typescript don't
  support it yet, hence Biome and hand-written API types.
- Rust stable (edition 2024), Tauri 2.12 with the single-instance, updater, dialog, opener,
  notification and autostart plugins, and its tray icon.
- No Dependabot: it opens branches. Dependencies are updated on `main` with the routine in
  [docs/development.md](docs/development.md).

**Delivery**
- GitHub repo `frankgrobbelaar/kura`, public under the MIT licence (the owner's call on
  2026-10-10, replacing private releases through the `gh` login); the app's identifier is
  `io.github.frankgrobbelaar.kura`. Anyone may fork; only collaborators can open pull requests
  (a repo setting) and issues are off: no contributions. Secret scanning with push protection is
  on: GitHub refuses a push that holds a known secret. CI on every push to `main` (Windows
  runners).
- Semantic versions and a changelog (the owner, 2026-10-11): patch for fixes, minor for features,
  major for a change to act on. `scripts/release.mjs` picks the version, moves CHANGELOG.md's
  "Unreleased" entries under it, commits and tags; it and the release workflow refuse a version
  that isn't newer than the last, so every release is an update.
- The owner releases from GitHub's site when happy with `main` (2026-10-11): Actions › Release ›
  Run workflow. On `main` it checks CI passed, runs `release.mjs`, builds and checks the
  installer, and only then pushes the release commit and tag together and publishes. The commit
  carries the name and no-reply address of whoever started the run. A tag pushed from a PC still
  releases too.
- A `v*` tag builds the NSIS installer, signs it for the updater, and publishes a public release
  with its notes (the changelog entries, every commit since the last release, a comparison link),
  `latest.json` (which carries the entries to the update card) and `THIRD-PARTY-NOTICES.txt`. The
  workflow then checks that `releases/latest/download/latest.json` names the new version, which
  installed copies check daily, no login needed, and refreshes the downloads page.
- Downloads page (the owner, 2026-10-11): https://frankgrobbelaar.github.io/kura/, the repo's
  website on GitHub Pages, lists every version newest first with its notes, installer, size and
  SHA-256. Kura's "Every version" buttons open it.
- `THIRD-PARTY-NOTICES.txt` lists everything that ships, with its licence, and goes next to Kura
  with `LICENSE.txt`. `engine/tools/third_party_notices.py` writes it from what was actually
  bundled (PyInstaller's records, Cargo's graph, Vite's licence report) and stops the build on
  a licence that isn't allowed.
- **Every download is listed in the installer** (the owner, 2026-10-11: "really important"). No
  one installs anything by hand except a graphics driver, which Kura checks and links to. What
  isn't inside the installer (WebView2 on a PC without it, ffmpeg) goes in one manifest,
  `engine/src/kura/downloads.json`: what it's for, version, size, licence, source and checksum.
  The installer's first page lists it (`scripts/installer-notes.mjs`), the first-run Tools step
  downloads Kura's part of it (`engine/src/kura/tools.py`), and Kura downloads nothing that isn't
  on it. Lookups (titles, episode lists, artwork from TMDB and AniList) aren't downloads of
  programs or data sets, and are named on the same page.
- Per-user install (no admin) into `%LOCALAPPDATA%\Programs\Kura`, apart from the data.
- The update-signing key is `%USERPROFILE%\.tauri\kura-updater.key` (no password) and the
  `TAURI_SIGNING_PRIVATE_KEY` repo secret. Lose it and installed copies can't update.
- Not code-signed (Windows SmartScreen warns once on first install); fine for a personal tool.

**The owner's PC**
- GTX 1660 Super 6 GB (Turing NVENC, no AV1 encode), i5-9600K (6 cores), 24 GB RAM, about 1.7 TB
  free on D: and F:. Graphics driver 617.42 (fine as it is; never install drivers). No ffmpeg
  installed: Kura fetches its own. GitHub CLI signed in as frankgrobbelaar.
- Its Windows SDK registry entry points at the wrong folder, so the user variable `RC` names
  rc.exe for Rust builds (see docs/development.md, "Troubleshooting").

## What's next

1. Identification and missing episodes: done (AniList and TMDB, the review screen, the gap
   check and its reports, the watcher, the scan's last three stages, and TMDB's credit line with
   its logo).
2. The library home and a page per title: done (the shelf of franchises and series sorted by
   release date, a page per franchise, "Needs your attention", the title page with "Open folder"
   and "Change match").
3. Tidy-up in the app: done (review title by title, apply, undo, quarantine on the same drive,
   History). Quarantine keeps copies for 30 days, then step 6's daily clear-out empties it.
4. Conversion, with the queue: done (the AI model and Anime4K, the encode and Kura's mux, checks,
   estimates and "See it first", nights only, full and unplugged drives, put back from History).
5. Settings: done (moving the data folder to another drive, and importing an export, too).
6. Background care: done (nightly backups with restore, the daily quarantine clear-out, the tray
   with "Start with Windows" and notifications).
7. Poster and background pictures next to each show, for media servers: done (optional, off
   unless turned on; the UI never names Plex).
8. The small-things board: done (a file open in another app, a crash or power cut, a failed
   conversion, a finished batch, being offline, a name that's taken: "(2)" beside it, "Compare
   the two" or "Skip"; not enough space: empty the drive's quarantine first, or convert what
   fits; records damaged past use: the newest backup that opens, or new records; and the
   overnight note: keeping the PC awake till 07:00, "Stop at 03:00" starting no file after 03:00
   that night, the one converting finishing).
9. Light mode: done (Paper, the owner's pick of three drafted on 2026-10-14, over A Daylight's
   cool grey and C Ink's white and black; as Windows is, or chosen in Settings › General).
10. A small player inside Kura's window: done (2026-10-14, to the
    [Kura Player](https://claude.ai/artifact/3MK2zSwv9fS1jzt2rP7Qw3) canvas the owner approved:
    Play beside each video on a title's page, "Play it" and the stills on "Which anime is this?",
    the small player over the page and dragged anywhere, full screen and back, sound and
    subtitles, chapters, the next episode, and its small things: getting it ready, a file that
    won't play, a drive that isn't connected, a file gone).
11. English for every episode, from the owner's own files, to the
    [Kura English Subtitles](https://claude.ai/artifact/RmbcFdZiDMXYvz69cQ9CYA) canvas the owner
    approved (2026-10-15): each video's sound and subtitle languages on its title's page and
    Home, and English subtitles made on the PC from its own sound, in the queue with the
    conversions, with the small things (the model first, waiting for the card, nothing said, a
    sound that won't read, English sound written down, taking them away), and English sound and
    subtitles added from another copy the owner keeps, in Tidy up's duplicates: done.
12. Kura on any PC, to the [Kura on Any PC](https://claude.ai/artifact/BRYamJpre3pLDT4ZZtPhaN)
    canvas (2026-10-15): what this PC can do in Setup and Settings › About, tested there;
    converting on AMD's and Intel's encoders as on NVIDIA's; times measured on this PC; the lighter
    way where the card is small or slow; the small things; and what a PC needs in the README and
    on the downloads page: done.
13. Kura 1.0 (2026-10-18), the eight under Decisions › Kura 1.0, drawn after building in
    [docs/design/one.html](docs/design/one.html) and the
    [Kura 1.0](https://claude.ai/artifact/7WBdCUmEhNuGVqpdpa3BKZ) page: file actions and a
    video's details, About, watched and picked up, Continue watching, Coming up, the health
    check, ticks, at a glance and choosing a poster: done, released as 1.0.0.
14. Details as a card with its picture (2026-10-19), the owner's pick on the
    [Kura Detail Options](https://claude.ai/artifact/6rp1m1fFNX5SmEKhDhgt7F) canvas (Decisions ›
    Details as a card): a video's or an episode's, a title a franchise lacks, choosing a poster
    and the videos that didn't play, with TMDB's pictures from episodes kept on their rows: done.

Licences, all settled (the owner, 2026-10-14). ffmpeg: Kura doesn't ship it; the first run
downloads an LGPL build (LGPL-2.1-or-later) from the source `engine/src/kura/downloads.json`
names, with its licence, as the installer's first page lists it. AniList: its API is free for
non-commercial use within its rate limit, and Kura keeps to it (one client the engine shares, which
waits when AniList says the minute's requests are spent; the franchise look-ups ask about 12 a
minute). TMDB's terms are met in the app: its credit line with its logo, in Settings (About, and
Titles and artwork). Real-ESRGAN's model (BSD-3-Clause) and Anime4K's shaders (MIT) are in
`engine/src/kura/assets` with their licences, which the notices carry.

Build each screen to its board in [docs/design/](docs/design/), with its empty, error and recovery
states.

## Guides and docs

- **Area guides.** [AGENTS.md](AGENTS.md) is the entry for any coding agent, and each area has its
  own: [engine/AGENTS.md](engine/AGENTS.md), [app/AGENTS.md](app/AGENTS.md) (the UI),
  [app/src-tauri/AGENTS.md](app/src-tauri/AGENTS.md) (the shell) and [docs/AGENTS.md](docs/AGENTS.md).
  Read the guide for an area before changing it: it says what belongs there, the patterns to copy,
  and what "done" means.
- **Docs.** [docs/README.md](docs/README.md) is the map: architecture, development, conventions,
  design, releasing, and one page per tool in [docs/stack/](docs/stack/). Read the stack page before
  changing how a tool is used, and update docs in the same commit as the code they describe.
