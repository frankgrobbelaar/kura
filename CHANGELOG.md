# Changelog

Every change to Kura you'd notice, newest first. Versions follow
[semantic versioning](https://semver.org): a new major number means something you have to act on,
a new minor number brings features, a new patch number fixes things. Every version can be
downloaded from the [downloads page](https://frankgrobbelaar.github.io/kura/), and an installed Kura
shows these notes when it offers the update.

## Unreleased

### Changed
- The engine is built with the newest versions of the libraries it uses: FastAPI 0.162 and
  Starlette 1.10.

## 1.4.0 - 2026-10-28

### Changed
- The window is built with the newest versions of the libraries it uses: React Router 8.5,
  TanStack Query 5.105, Lucide's icons 1.61 and Vite 8.3.5.

### Fixed
- A video named with only a mark after its episode ("Dragon Ball Z - 01 - .x") no longer stops
  the scan for good.
- An episode the show's list on TMDB doesn't have yet ("S10E05" while it lists nine seasons) waits
  for you, rather than being counted back into an earlier season, where it looked like a copy of
  that season's episode and Tidy up offered to set one of them aside.
- An episode titled "Part 2" after its code ("S01E05 - Part 2") is that episode, not the second
  part of its season.

## 1.3.0 - 2026-10-20

### Fixed
- A release that numbers a show straight through its seasons is found and filed without asking:
  "My Hero Academia - 159" in a "Season 07" folder goes to season 7, though AniList keeps each
  season apart. So are its films ("My Hero Academia Movie 01 - Two Heroes") and its OVAs by their
  names ("OVA - Training of the Dead!"), and a creditless ending among its extras ("[SP02] NCED -
  01") is an extra now, not a special. A bare number in a folder of a show's OVAs is one of its
  OVAs, and one among its films waits for you, rather than either being taken for an episode.
- Names in Japanese are found: 第01話 and 第2期, 劇場版 or Gekijouban for a film, 総集編 for a
  recap, full-width letters and digits, and a show's name in 【】 (and 第01集 from Chinese
  releases).
- More names are found as they're written: one that gives two ("Ore dake Level Up na Ken (Solo
  Leveling)"), a show's short English name ("Demon Slayer", "Seraph of the End"), scene names
  with dots ("Spy.x.Family.S01E01"), a film named as its folder ("Jujutsu Kaisen 0 (2021)", not
  an episode 0), and folders named after a show and its season ("[Group] Show Season 02", "Show
  2nd Season", "Show (Season 2)"). The videos waiting for a match are looked up again at the next
  scan.
- A video named with a circled number ("Show - ①") no longer stops identifying every video.

## 1.2.0 - 2026-10-19

### Changed
- A picture from an episode you haven't watched stays blurred till you ask ("Show the
  picture", and you can hide it again), as what happens in it does, since it can give the story
  away. Your show's own picture, when there's none from the episode, isn't blurred, and a film's
  card shows the film's own picture rather than a frame from it.

## 1.1.0 - 2026-10-19

### Changed
- A video's or an episode's details open in a card over the page rather than a panel at its
  side, with a picture from the episode across its top (TMDB's, or a frame from the video) and
  Play on it, from where you stopped. What happens in it waits behind a blur till you ask, and
  the episode before and after it sit at the card's foot, to go along without closing it.
- A title a franchise lacks opens as a card too, its cover across the top, and so do choosing a
  poster and the videos that didn't play.

## 1.0.0 - 2026-10-18

Kura 1.0, the first version meant for everyday use. There's nothing to do on your part: it
updates as any version does, and keeps everything you have.

### Added
- A title's page says what it's about: its synopsis, genres, studio, when it aired, where it
  stands and how long an episode lasts, as TMDB and AniList tell it, with its pages on both.
- A franchise's page says what it's about and the years it spans, and a title you don't have
  opens to show what AniList knows of it: its synopsis, studio, genres and its page there.
- Show a video in its folder or copy its path, from its row's menu wherever it's listed: a
  title's videos, the queue, "Which anime is this?" and Tidy up.
- A video's details: its episode's title and air date, what happens in it (hidden till you ask,
  as it gives the story away), its picture, sound and subtitle tracks, length, size, where it is
  and what converting it would do. Open them from the video's name or its menu; an episode you
  don't have opens from the episode map or the missing list, a special from its list.
- Kura remembers where you stopped: Play picks a video up there (with "Start over" for a moment),
  a title's videos tick off the ones you've watched and say what's left of one you stopped, and
  each video's menu marks it watched or not.
- "Continue watching" on Home: each title you're part way through, the latest first, with the
  video you stopped or the next one up, played from where you left off.
- "Coming up" on Home: each of your shows with an episode still to come, its next one and the day
  it airs. On the day one airs, Kura tells you, once, unless you have it already.
- A health check: overnight, while nothing converts, Kura plays a few seconds of every video at
  three points, a few at a time, and again a month on, so a file damaged since shows before you
  want it. What didn't play is listed on Home, to play and see, try again, call fine or mark as
  broken: nothing changes till you say. It's on unless you turn it off in Settings › Libraries.
- Tick a title's videos to do several at once: mark them watched or not, convert them, make their
  English subtitles or delete them. A whole season ticks at once.
- "At a glance" on Home: how long your library plays end to end, how much of it you've watched,
  what converting saved (or used, for the bigger picture), and the titles taking the most room.
- Choose a title's poster: click it on its page for TMDB's posters (in English, Japanese or
  without words) and AniList's cover. Your choice stays as the episode lists are refreshed, and
  the poster next to the show follows it.

### Changed
- Long names on the shelf's cards wrap onto a second line rather than trail off.
- One card needing your attention on Home is a card wide, rather than the whole row.
- Deleting a video, on a title's page or "Which anime is this?", is in its ⋮ menu now, as
  "Delete…", beside what else you can do with it.
- Sizes of a terabyte or more read in terabytes everywhere ("1.2 TB"), as Home's summary does.

### Fixed
- A title's page opens several times faster in a library of thousands of videos.

## 0.19.0 - 2026-10-15

### Added
- Search the whole library from the title bar: anime by any name they go by ("DBZ" too, where
  AniList knows it), episodes by code or name ("S04E11", "Ginyu"), the ones you're missing
  included, and videos by their files' names. What it finds is listed as you type, the closest
  first; the arrow keys and Enter, or a click, open it. An episode or video opens on its title's
  page, its videos searched for it.
- Filter History by anime or file, through all of it, a week of the days it finds anything on at
  a time.

## 0.18.0 - 2026-10-15

### Added
- Search the lists that grow long: Home's shelf (a franchise by its name or any of its titles'),
  a franchise's titles (the ones it's missing too), a title's videos through every season (by
  episode code, episode title or file name), Convert's What, the queue's Up next and Tidy up's
  changes. The list narrows as you type, however a name is written ("pokemon" finds "Pokémon"),
  and going back to the page finds the search as you left it. In the queue, ticking every file
  ticks the ones found; in Tidy up, applying applies the changes found.

## 0.17.2 - 2026-10-15

### Fixed
- A title's videos no longer say "unnamed" for sound whose file doesn't name its language. They
  name the language Kura heard there when it made English subtitles from it, or else say
  "Language not labelled". A language a video's files write two ways ("jpn" and "ja") shows once,
  and every language Whisper knows has its name.

## 0.17.1 - 2026-10-15

### Fixed
- Testing the PC while Kura made English subtitles no longer stops Kura's engine, nor does "See
  it first" with Best quality: loading the AI model beside Whisper crashed the graphics driver. Both
  now run the AI model in a process of their own, so a driver that fails takes only that with it,
  and the AI model and Whisper take turns on the graphics card a frame or a word at a time.

## 0.17.0 - 2026-10-15

### Added
- Kura on any PC: Setup's last step, now "Tools and this PC", tests what this PC can do once
  ffmpeg is there (about a minute) and says it part by part, with how long an episode takes:
  converting, the AI upscale for SD, the fast upscale for 720p, English subtitles and the player.
  Settings › About shows the same under "This PC", with "Test again" for a new graphics card or
  driver.
- Converting on AMD's and Intel's graphics, with their own HEVC 10-bit encoders (AMF and Quick
  Sync), as on NVIDIA's. A PC without such an encoder says so on Convert, and what still works
  there; one whose card needs a newer driver links its maker's drivers.
- Times measured on your PC: Convert, the queue and Make English subtitles use this PC's own
  speeds, from the test and then from every file converted and every video's subtitles, and say
  when they're still a guess, with "Test this PC".
- A way that's slow on this PC says "Slow here": the AI model, at over three hours an episode,
  has the fast upscale chosen first, and Convert says Re-encode only is much quicker where the fast
  upscale is slow. One that can't run there says why and can't be chosen, and SD files get the fast
  upscale instead.
- English subtitles on smaller cards: Best wants a graphics card with 4 GB of its own memory, so
  on one with less Fast is chosen ("Right for this PC"), and runs on the processor where the card
  hasn't the 2 GB Fast wants. A card that runs out of memory for Best says so, with "Make them
  with Fast".
- The README and the downloads page say what a PC needs for each part of Kura.

### Fixed
- The AI model and Whisper run on a laptop's own graphics card, not the processor's graphics
  that drive its screen.
- On a PC whose graphics card can't run the AI model, it no longer runs it on the processor by
  itself, which would have taken days an episode.
- Whisper on the processor loads: before, its half-precision model wouldn't, so English subtitles
  failed on a PC whose card couldn't run them.

## 0.16.0 - 2026-10-15

### Added
- English subtitles for the videos that have none, made on your PC from each video's own sound:
  "Make English subtitles" on a title's videos (or on Home) takes a season, the whole title or
  everything without English, the sound to translate from, Best or Fast, and when. They wait in
  the queue with the conversions, one at a time on the graphics card, and go beside each video
  under the name media server apps read; the video itself never changes. The speech model they
  need (1.5 GB for Best, 486 MB for Fast) is downloaded the first time you ask, from the source
  the installer's first page lists, and checked before it's used.
- A title's videos say what each can be heard and read in (its sound, and its subtitles in the
  file or beside it), mark the ones with no English, and show English subtitles being made or
  waiting in the queue; the title sums it up for all its videos.
- Home shows your videos by language, and how many have no English at all, with the way to make
  subtitles for them.
- The player marks the English subtitles Kura made, and says names and jokes can be off.
- History lists each batch of subtitles Kura made, and takes a batch away again: to quarantine,
  from where History puts it back till it's cleared out. Subtitles you've edited since are yours,
  and stay.
- English from another copy: when Tidy up finds two copies of an episode and the one it sets aside
  has English sound or subtitles the one kept hasn't, it offers to add them to the one kept. Kura
  lines the two up by the sound both have, checks the result before it takes the file's place, and
  sets both copies as they were aside together, which History puts back. Copies that aren't the same
  cut stay as they are, and Tidy up says why the next time.

### Fixed
- History puts a file's latest change back first: a file converted again since has that conversion
  put back before the earlier one, which before could take the newer file away and then the original
  too.

## 0.15.1 - 2026-10-15

### Fixed
- Picking another sound or subtitles in the player's menu with the mouse did nothing: the click
  was taken as the start of moving the player. The menu takes it now.

## 0.15.0 - 2026-10-15

### Added
- A film's page has Play at the top, as does any title that's a single video.

### Changed
- A title's videos come a season at a time: pick the season above them (the specials have their
  own), and a long season scrolls in its place instead of running the page on. Each video shows
  its episode's title, picture, length and size rather than its whole path, which shows when you
  point at it, and a season's name under Seasons takes you to its videos.

## 0.14.0 - 2026-10-14

### Added
- A player inside Kura. Press Play beside any video on a title's page, or on "Which anime is
  this?" (Play it, or a still to play from there): it plays small over whichever page is open,
  you can drag it anywhere in the window, and it goes full screen and back (the next episode
  too). Choose the sound and subtitles the file has, find its chapters marked on the bar full
  screen, and play the next episode with a click.
  Subtitles in the file join a moment after the picture, as Kura reads them out of the file
  first, and the sound and subtitles you picked start the next video too. A file that won't
  play, a drive that isn't connected or a file that's gone says so, with what to do.
- History comes a week at a time, with "Show older" for the days before, and a busy day shows its
  first 20 entries till you ask for all of them. An undo shows on the day you made it, and a day
  from another year says its year.
- Clear History: keep its last 24 hours, 7 days or 30 days, or nothing, after Kura asks. Or have
  Kura clear what's older than 7, 30 or 90 days each day, in Settings › Your data (it keeps
  everything till you choose). Clearing never touches your files, and what still has a copy in
  quarantine stays listed, so you can put it back.

### Changed
- Kura says plainly that it's for videos you have the right to keep and watch: it looks after
  the files on your PC, plays them only in its own window, and never searches for, downloads or
  shares video. Settings › About, the downloads page and the new README say so.
- The naming example in Setup and Settings uses a made-up title, as the README's pictures of
  Kura do.

### Fixed
- Kura's engine could crash after a library folder went away and came back while Kura watched
  it (its drive unplugged and plugged in again, say): Windows was told twice to let go of the
  folder, the second time letting go of another file of Kura's.
- Converting a 720p file failed when the folder Kura is installed in had an apostrophe in its
  path (a Windows user name like O'Brien): ffmpeg read Anime4K's file without it.

## 0.13.0 - 2026-10-14

### Added
- Light mode, in warm paper tones: cream panels on a paper ground, deep ink text and the same
  amber. Kura is light or dark as Windows is, changing when Windows does, or keeps to the one you
  choose in Settings › General.

### Changed
- The queue's Today keeps its failed files to a height and scrolls them in their place, instead
  of running the page on with a card for each.

### Fixed
- Converted files were thrown away as not playing ("non monotonically increasing dts") when they
  played well: Kura's check rounded two frames' times to one at some points, and took that for
  damage. Those conversions go back in the queue by themselves, with their originals untouched.
- The update card's list of what's new has its amber dots again.

## 0.12.0 - 2026-10-14

### Added
- Every page shows its shape while it loads: grey placeholders where its header, cards, panels
  and rows will be, instead of an empty page. They breathe softly, and hold still when
  Windows' animation effects are off.
- The queue's Up next has a box to tick every file waiting at once, beside its heading.

## 0.11.0 - 2026-10-13

### Changed
- A title's episode map goes season by season: each season's episodes on a row of their own,
  named, instead of one long block of squares.

## 0.10.0 - 2026-10-13

### Added
- The side bar says what's going on, as the design showed: Convert shows how far the file
  converting now has got (63%), or how many files wait to convert, and Tidy up how many changes
  and files to match wait for you.
- The queue takes several files at once: tick files, or a whole season or title, and convert
  them next, move them to the end or take them out of the queue together. Every season and title
  waiting can be opened to its files, not only the first.
- "Cancel all" beside "Pause all" empties the queue and stops the file converting now, once you
  say so. Your files stay as they are.

## 0.9.0 - 2026-10-13

### Added
- A title's page has "Missing titles" too, when its franchise has titles you're missing: it
  leads to the franchise's page with them shown, even for a title that's alone in your library.

### Changed
- Missing titles are dotted placeholders among your own, their cover dimmed inside, and they
  show up sooner after Kura starts: it looks up what you're missing before your own titles.

## 0.8.0 - 2026-10-13

### Added
- A franchise's page can show what you're missing of the whole franchise: "Missing titles",
  beside the sort, puts in the series, films, OVAs and specials you have no part of, each in its
  place, dimmed and marked "Not in library" ("Coming" for one not out yet). Kura looks each
  franchise up on AniList in the background, a few entries at a time, and keeps it current,
  so a new one, such as Dragon Ball Super: Beerus, appears by itself.

## 0.7.0 - 2026-10-13

### Added
- A scan says what it changed: Home, beside Scan again, says when the last one ran and what it
  found new or gone ("1 gone"), the scan page does too, and History lists it with each scan.

### Changed
- Home's videos by picture are a summary at the top, and Scan again and Add a folder sit by the
  page's title.

### Fixed
- A video added to or removed from a library folder shows within moments. Kura now scans five
  seconds after the folder goes quiet (it could wait half a minute), and every screen catches up
  once the scan ends. A scan quicker than a second, as most are, used to go unseen, so nothing
  showed the change until you moved to another page.
- The queue's "Now converting" keeps its full height when the queue is long: it was squashed to a
  thin strip.

## 0.6.0 - 2026-10-13

### Changed
- Titles are listed by type: series first, then movies, OVAs and specials, each oldest release
  first (or by name). A franchise's page shows each type under its own heading, Home's shelf puts
  franchises first, and Convert lists a franchise's series before its films. "Recently added"
  and "Most missing" still list every type together.

## 0.5.0 - 2026-10-13

### Added
- Names AniList can't find are looked up on TMDB too, which knows more languages and spellings
  (with your TMDB key): AniList is then asked for what TMDB calls it. A file named in Spanish,
  say, is found as the show TMDB knows by that name, and the review screen's search does the
  same. Files waiting for a match are looked up again at the next scan.
- A special its show's list doesn't name the way the file does is looked up by its own name, as
  an OVA or special of its own: "Special 05 (GT) - A Hero's Legacy" is found as Dragon Ball GT's
  special, and goes among a show's specials by the day it first aired when the show is yours.

### Fixed
- A film named with its series' initials is found: "Dragon Ball Z - Movie 16 - DB Super BROLY"
  is Dragon Ball Super: Broly.
- A special's name matches its show's without the words any special carries: "Summer Vacation"
  is "Summer Vacation Special". Accents don't count when names are compared ("Pokémon" is
  "Pokemon").

## 0.4.0 - 2026-10-13

### Added
- Choose your standard on Convert too, and the estimates follow at once. Once everything is at
  one standard, the page offers the other. Change it, and what's at the old one can be converted
  to the new, Kura's own conversions too: from the converted file, or from its original if you put
  that back from History first.
- Converted files' originals: keep them in quarantine, as before, or delete each once its result
  is checked and in place (Convert, and Settings > Your data). Room for converting is reckoned to
  match, and a deleted original can't be put back.

### Changed
- Each way on Convert says what it really does for the files chosen: when they need no
  upscaling, every way only re-encodes them and takes the same, and the page says so. A smaller
  standard saves space more than time, which the page says too: the fast upscale is quicker
  making 720p, but the AI model and re-encoding take as long, working on the source.

### Fixed
- History no longer offers to put back a converted file's original once it's gone, cleared out
  or deleted: it says the original was deleted.
- The files set aside as not anime were out of reach while no file needed a match: Tidy up now
  shows how many there are, leading to Which anime is this?, where they're listed.

## 0.3.0 - 2026-10-13

### Added
- Check for a new version (Settings > Updates): Kura looks at once instead of waiting for its
  daily check, which carries on as before, and says when it last looked. A version it finds can
  be installed from there too, even after Later on its card.
- Delete a file waiting for a match, from Which anime is this?: the bin beside it, or beside a
  file up next. Kura asks first, then moves it to the quarantine on its drive with its
  subtitles, like any delete; the page offers it back right after, and History till the
  clear-out.
- Files set aside with Not anime, ignore it are listed on Which anime is this?, so one can be
  matched after all or deleted. Until now nothing showed them again.

### Fixed
- Updated to 0.2.0, Settings still said Kura 0.1.0: the update had left the old engine's files
  beside the new one's, and the engine read its version from the old ones. An update now
  replaces the engine whole, and this one clears what the last one left.

## 0.2.0 - 2026-10-13

### Added
- Keep Kura running when you close the window (Settings > General): on, closing the window
  leaves Kura in the tray, still at work; off, it quits Kura, whether or not Kura starts with
  Windows. Until you choose, closing does as before.

### Changed
- Home shows just your library: what it said about this copy of Kura (the engine, the data
  folder, the database, TMDB and updates) is in Settings > About now.

### Fixed
- The nav rail keeps your place: Home stays lit on the scan, a franchise's page and a title's
  page, and Tidy up on "Which anime is this?".
- Films a release numbers among its series' ("Dragon Ball Z - Movie 03 - The Tree of Might") are
  found by their own names, and specials and OVAs go among their show's specials by theirs
  ("Special 06 - The History of Trunks"). A series AniList writes otherwise ("Dragonball GT") is
  found too, and a year in brackets with more in them, "(1990 BluRay)", counts. The files waiting
  for a match are looked up again at the next scan.

## 0.1.0 - 2026-10-12

### Added
- The AI model reports nothing to Microsoft: ONNX Runtime, which runs it, has its usage reports
  (on by default in its Windows builds) turned off.
- While the nights-only queue converts at night, the queue says it's keeping the PC awake till
  07:00. Stop at 03:00 ends that night's run early: no file starts after 03:00 (the one
  converting finishes), so the PC can sleep sooner; Go on till 07:00 takes it back.
- Records damaged so badly they won't open (a disk fault, a power cut mid-write) no longer stop
  Kura starting: it says so, offers the newest backup that opens, and keeps the damaged file
  beside the records as it is. With no backup, it starts again with new records, as on its first
  day. When it was the disk that couldn't read them (a drive away a moment), Try again comes
  first. While Kura waits in the tray, a notification says so.
- Not enough space: when a drive hasn't room for what's queued, the queue pauses and says what
  the files there need and what's free. Empty quarantine first (Kura asks once more, since
  what's set aside there goes for good), or convert the ones that fit now: the rest wait for room
  while the others go, and start by themselves once there is. The Convert screen asks the same
  before queueing a choice that doesn't fit.
- A file open in another app (a player playing it) as its conversion finishes no longer fails:
  the queue says so, keeps the converted copy beside it, goes on with the next file, and puts the
  copy in place once the app lets go, trying every 5 minutes or at once with Try now. Skip this
  file throws the copy away. A tidy-up that meets a file open elsewhere says so in Kura's words.
- Poster and background pictures next to each show and film (Settings > Your data, off unless you
  turn it on): `poster.jpg` and `fanart.jpg`, which media servers show. Kura never writes over a
  picture that's there, and turning it off takes away only the ones it wrote, unchanged. Change
  a match, and Kura's pictures of the old title make way for the new one's.
- Import an export (Settings > Your data), from this PC or another: Kura's records become the
  export's as its engine starts again, and what it knew till then is backed up first, so
  Backups can bring it back.
- Move Kura's data to another drive (Settings > Your data): Kura copies it, checks the copy, and
  only then removes the old one, as its engine starts again, however long that takes. A move cut
  short (a power cut) is settled when Kura next starts. A folder on another computer isn't
  taken: the data needs a drive of this PC's own (an external one is fine). If the drive it's on isn't connected,
  Kura says so instead of starting empty, and uninstalling cleans up only Kura's own files
  there.
- Start with Windows (Settings > General): Kura waits in the tray, so the queue, the nightly
  backup and the watching carry on, and closing the window keeps it there. While it's in the
  tray, a Windows notification says when a batch is done ("Trigun, season 1 is done · 26
  episodes · all checked") or when a full drive paused the queue; a click opens Kura. With the
  window open, the same shows as a note at its foot, with View leading to the title (or History,
  or the queue). If Kura can't run there (its data's drive isn't connected yet, say), a
  notification says why, and it tries again by itself.
- Delete a title, a season or one video from its page. Kura asks first, then moves the videos and
  their subtitles to the quarantine on their drive, for as long as you keep copies set aside; the
  page, right after, or History puts them back. A video another app has open stays (the page
  says so), and subtitles another copy of it shares stay with that copy.
- Only the page scrolls: the nav rail and the page's title (or where it sits) stay where they
  are, and so does Settings' list of sections.
- A title's gap analysis reads like a document (headings, lists and tables), under the title Gap
  Analysis.
- TMDB's logo sits beside its credit line on Home and in Settings, as TMDB's terms ask.
- Files are named "Clean names" or "Keep my names": Kura's words don't name a media server.
- Backups: every night at 03:00 (or the first chance after), Kura backs up its records, keeping
  the last 7, each checked as it's made and never written over. Settings shows the last one,
  makes one now (kept apart from the nightly ones), and restores one: the backup is checked
  first, Kura's records go back to then, your files stay as they are, and what Kura knew till
  then is backed up first, even when it doesn't check out.
- What waited in quarantine longer than you keep it (30 days unless you choose otherwise) is
  cleared out once a day while Kura is open. A converted file's original goes only once its
  converted copy is in place. Whatever its records say, Kura deletes nothing but what's in its
  quarantine folders, its own unfinished copies and its own pictures.
- Settings: your anime folders, the standard and how files are named (changed at once), the
  TMDB key, where Kura's data lives and how big each part is, the export to a folder you pick,
  whether a gap report goes next to each anime, how long copies set aside are kept, updates, and
  what Kura is made of.
- Convert: choose what to convert (a franchise, a title, or some of its seasons) and how: Best
  quality with the AI model for SD, Fast with Anime4K, or only a re-encode. See it first: a frame
  of one file before and after, at three points, with a handle to drag between them. Before
  queueing, it says what that takes: GPU time, size before and after, and whether each drive has
  room. Queue it to start now, on nights only, or after what's waiting. Every file goes to your
  standard, and none gets more than suits it (the AI model is for SD).
- The queue converts one file at a time while Kura is open, showing the graphics card's load and
  temperature. Pause it (Space), skip a file, move one up, take one out, or run it on nights only
  (23:00 to 07:00). Each result is checked (length, streams, a test play) before it takes its
  original's place; the original waits in quarantine for 30 days and can be put back from
  History, which lists every conversion with what it made. A file whose drive isn't connected
  waits while the others go; a file that fails says why and how far it got (one whose original
  can't be read, how far that plays), shows what ffmpeg said last, copies its whole log, and can
  be marked broken (it's then counted among the files that won't play, till it changes); a drive without room for the result pauses the
  queue and says so; and a file whose new name is taken (an MKV beside an MP4 of the same name)
  says so before converting. Paused once its result is made, a file is still checked and put in place, and a
  file saved over while it converts keeps what was saved. Kura keeps the PC awake while a file
  converts, and nothing it starts keeps running once it's closed.
- Tidy up: Kura proposes where every identified video goes (`TV\Show (Year)\Season 01`,
  `Movies\Title (Year)`), title by title: moves out of folders holding several anime, renames in
  place, and second copies of an episode set aside in a quarantine folder on the same drive, the
  two compared with a swap if you'd rather keep the other. Leave out any title, then apply.
  Subtitles move with their video (and stay with one that couldn't move), emptied folders
  go, and every video keeps what it was identified as. A film in two files (CD1, CD2) is
  filed as its two parts. With "Keep my names", files move into the same folders under the
  names they have. A name another file has already gets "(2)", and the review says so: Kura
  never overwrites a file. Compare the two side by side, or Skip that one, which stays where it
  is with its subtitles this time. Applying makes
  exactly what you reviewed, or asks you to look again if a scan changed it, and waits while a
  scan runs.
- History: every tidy-up and scan by day, newest first. Any tidy-up can be undone there (or right
  after applying it), putting every file back; a file that couldn't go back can be tried again.
- Home lists every franchise and series as poster cards, oldest release first, or by name,
  newest added or most missing. A franchise (Dragon Ball's series, films, OVAs and specials) is
  one card with a page of its own that lists them the same ways. Each says whether it's a TV
  series, movie, OVA or special, and how much of it is there.
- Home's "Needs your attention": files that need a match, episodes missing, files that won't play
  and folders holding mixed anime, each leading to what to do.
- Offline, Kura says so at the foot of the window: new titles and artwork fill in once the PC is
  back online, and everything else keeps working.
- After Kura closed unexpectedly (a crash, a power cut), Home says what it settled as it started
  again ("One file was restarted from the beginning; the original was never touched and nothing
  was lost."), with the way to History.
- A page for each anime: how much of it is there, its seasons and episode map with every
  episode's state by shape, the missing and broken episodes (a long run of missing ones as one
  range), its specials and OVAs apart, its videos, and the gap analysis written next to it (shown
  in its folder or copied). "Open folder" opens its folder in Explorer (or says why it can't),
  and "Change match" picks another anime for all its files at once: specials stay specials, and a
  file that doesn't fit the new anime waits for you, the title page says how many.
- Scans identify every video: which anime, movie, OVA or special it is and, with a TMDB key,
  which season and episode, numbered as TMDB lists them. Files Kura isn't sure about wait for you
  instead of being guessed. Offline, the scan still finishes and identifies them next time.
- The scan screen follows every stage: finding, reading, identifying each anime, checking for
  gaps and writing the reports, with the anime found so far (artwork and all, oldest release
  first), the files that need a match, folders with mixed anime and broken files.
- "Which anime is this?": for each file Kura couldn't place surely, its stills, length, picture,
  languages and group tag beside Kura's best guesses (press 1, 2 or 3), a search for another,
  whether it's an episode, a movie or a special, and which episode when its name doesn't say. One
  choice can cover the other files from the same release, and it's remembered, so a rescan never
  undoes it. "Not anime" leaves a file out for good.
- A gap analysis next to each anime that has a folder of its own (`Kura - Gap analysis.md`): the
  episodes TMDB lists as aired that the library doesn't hold (without a TMDB key, AniList's count
  of the episodes aired so far), a run of them as one range, with specials and OVAs listed apart
  and never counted as missing.
- Kura keeps the library current while it's open: it catches up at start on what changed while it
  was closed, notices videos and folders added, removed or renamed in your library (and a drive
  plugged back in) and scans once copying is done, and checks for new episodes every hour for
  shows still airing (weekly for finished ones).
- Setup takes your TMDB key, for episode lists, episode titles and artwork. It's optional: Kura
  checks the key with TMDB, then keeps it on this PC only, encrypted for your Windows account and
  never in an export. Home says whether TMDB is connected, and a key added later sorts what's
  already matched into TMDB's seasons.
- First-run setup in four steps: where Kura keeps its data, your anime folders, your standard and
  how files are named, and the tools Kura needs, with a quick check of the graphics card.
- Kura downloads ffmpeg (77 MB) the first time it needs it, and uses it only after checking it
  matches what Kura expects. If a part of it goes missing or it stops working, Kura offers the
  download again.
- The installer's first page lists everything Kura downloads to your PC, with what each is for,
  its size, licence and source.
- Scanning: Kura finds every video in your folders, whatever their layout, and reads each one's
  length and quality. A scan can pause, carries on after a restart, and later scans only read
  what's new or changed, plus any file that couldn't be read last time. Nothing in your folders
  is renamed or moved.
- Home shows your library at a glance: how many videos, how big, and how many are SD, 720p, 1080p
  or larger.
- The export now includes a list of every video in your library.
- A screen that fails to draw, or whose data Kura's engine couldn't give, says so and offers to
  try again, instead of going blank.
- Kura's window in the Cinema design, with its own title bar. Starting Kura a second time brings
  the open window forward.
- The engine that does Kura's work starts and stops with the window, and Kura notices if it stops
  on its own and starts it again.
- Kura updates itself: it checks once a day, downloads a new version in the background, shows
  what's new in it, and asks before restarting.
- Every version and what changed in it are on the downloads page, which the update card and the
  Home page open.
- Export: one zip with Kura's database, settings, every file change and a manifest.
- The installer puts Kura in your user folder without admin rights, offers an export before
  uninstalling, and never touches your anime files.
- A third-party notices file next to Kura lists every open-source part inside it, with its licence.

