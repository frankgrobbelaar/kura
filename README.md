# Kura

**The anime companion for your media server.**

A media server streams your library to every screen. Kura gets the library right first. It
recognises every episode, film and OVA in your folders, shows you what's missing, files everything
the way popular media server apps expect, brings every video up to one standard, with AI
upscaling for old SD episodes, and makes English subtitles for the ones with none. Kura (蔵,
"storehouse") runs on your Windows PC beside the server you already use, and changes nothing until
you say yes. It's for the videos you already have: Kura never finds, downloads or shares anime.

<p align="center">
  <br>
  <a href="https://frankgrobbelaar.github.io/kura/"><img src="docs/readme/download.svg" alt="Download for Windows" height="52"></a>
  <br>
  <sub>Free and open source · No account · Windows 10 and 11</sub>
  <br>
  <br>
</p>

![Kura's home: your library by picture, by language and at a glance](docs/readme/home.png)

## Made for anime

Anime libraries are rarely tidy: long series numbered straight through where seasons are
expected, specials and OVAs in odd places, films that sit between series, file names in every
style, SD beside HD. Media server apps match files by their names and folders, so an untidy
library shows up with gaps, the wrong seasons and missing artwork. Kura puts the library itself in
order and tells you what's missing, so your media server finds every file where it should be.

## How it works

### 1. Point it at your folders

One anime per folder, a franchise in sub-folders, or everything in one heap: Kura reads every
video (length, picture, sound and subtitles) and finds each one on AniList and TMDB. Anything it
isn't sure of waits for you on "Which anime is this?", with stills and a quick look at the file.

![Which anime is this? Stills, what reading the file showed, and Kura's best guesses](docs/readme/match.png)

### 2. See what's missing

Every title gets a page: what it's about, its seasons, an episode map, the episodes that aired
that you don't have, and a gap report beside the files. A franchise's page even shows the films
and OVAs you have none of, each in its place, and keeps watching for new ones. Home lists the
episodes still to come of the shows you have, by the day they air.

![A franchise's page, the titles you're missing as dotted placeholders](docs/readme/franchise.png)

### 3. Tidy up

Kura files everything in the layout media server apps read, `TV\Show (Year)\Season 01\…` and
`Movies\Title (Year)\…`, with subtitles moving alongside. It proposes the changes title by title;
nothing moves until you apply them, and History undoes any of it.

![Tidy up: what Kura proposes, a title at a time](docs/readme/tidy.png)

### 4. Bring it all to one standard

Choose 1080p or 720p and Kura encodes HEVC 10-bit on your graphics card. SD gets an AI upscale
from Real-ESRGAN's anime video model, 720p gets Anime4K's, and "See it first" shows a frame before
and after. The queue can run at night, waits when a drive is full, and checks every result before
it replaces the original.

![The queue: the file converting now and what's next](docs/readme/queue.png)

### 5. English for every episode

An episode with no English, neither a dub nor subtitles, gets English subtitles made on your own
PC: Kura listens to its sound and translates it, a season or the whole library at a time,
overnight if you like. They go beside each video under the name media server apps read, so your
server shows them too, and the video itself never changes. Kura marks them as its own, since names
and jokes can come out wrong, and History takes them away again. And when you have two copies of
an episode, the better picture can keep the other's English: Kura lines the two up by their sound
and adds it.

![Make English subtitles: which videos, from which sound, how good, and what it takes](docs/readme/subtitles.png)

### 6. Check it, right there

A small player is built in, for a quick look or a whole episode: it floats over the page wherever
you drag it, and goes full screen with the sound and subtitles the file has. It remembers where
you stopped, and Home picks up what you're part way through. Overnight, Kura test-plays every
video, so a file damaged since shows before you want it. Your media server does the rest, on the
TV, the phone or wherever you watch.

![The player full screen, sound and subtitles open](docs/readme/player-full.png)

## Alongside your media server

<table>
  <tr>
    <td nowrap><b>Same folders</b></td>
    <td>Kura works on the folders your media server already watches; its next scan sees the changes.</td>
  </tr>
  <tr>
    <td nowrap><b>Its layout</b></td>
    <td>Show and season folders and file names as media server apps read them: no release tags, resolutions or codecs.</td>
  </tr>
  <tr>
    <td nowrap><b>Its pictures</b></td>
    <td>Poster and background images beside each show, if you want them, for servers that use them.</td>
  </tr>
  <tr>
    <td nowrap><b>Hands off</b></td>
    <td>Kura never touches your media server, its database or its settings.</td>
  </tr>
</table>

## Safe by design

<table>
  <tr>
    <td nowrap><b>Asks first</b></td>
    <td>Renames, moves, deletions and conversions are proposed, then applied on your word.</td>
  </tr>
  <tr>
    <td nowrap><b>Undoes</b></td>
    <td>History puts back any tidy-up, and any converted file's original.</td>
  </tr>
  <tr>
    <td nowrap><b>Keeps copies</b></td>
    <td>What's replaced or deleted waits 30 days in quarantine on its own drive.</td>
  </tr>
  <tr>
    <td nowrap><b>Checks</b></td>
    <td>Every video is test-played overnight; what didn't play waits for you, and nothing changes till you say.</td>
  </tr>
  <tr>
    <td nowrap><b>Stays local</b></td>
    <td>No account and no cloud; nightly backups and a one-zip export.</td>
  </tr>
</table>

## The AI inside

Every model runs on your own PC, and no video or sound leaves it. The upscalers and the voice
detector ship inside Kura; Whisper is downloaded the first time you make subtitles, from the
source the installer's first page lists.

<table>
  <tr>
    <td nowrap><b><a href="https://github.com/xinntao/Real-ESRGAN">Real-ESRGAN</a></b></td>
    <td>Its anime video model, <code>realesr-animevideov3</code>, upscales SD episodes (480p and 576p). BSD-3-Clause licence.</td>
  </tr>
  <tr>
    <td nowrap><b><a href="https://github.com/bloc97/Anime4K">Anime4K</a></b></td>
    <td>Version 4.0's mode A (HQ), small neural networks written as graphics shaders, upscales 720p to 1080p. MIT licence.</td>
  </tr>
  <tr>
    <td nowrap><b><a href="https://github.com/openai/whisper">Whisper</a></b></td>
    <td>OpenAI's speech model hears an episode's sound and writes it in English: medium for Best, small for Fast, on your graphics card (Fast on the processor when the card hasn't the memory). MIT licence.</td>
  </tr>
  <tr>
    <td nowrap><b><a href="https://huggingface.co/pyannote/segmentation-3.0">pyannote</a></b></td>
    <td>Its speaker segmentation model 3.0 finds where someone speaks, even over music, so Whisper hears just that. MIT licence.</td>
  </tr>
</table>

## Your own videos only

Kura looks after video files that are already on your PC, and plays them only in its own window.
It never searches for, downloads or shares anime or any other video, nor subtitles or sound
tracks (the English subtitles it makes come from your own video's sound), never streams video over
the internet, and doesn't get around copy protection. Use it only with videos you have the right to
keep and watch: Kura is not for piracy, in any form.

Kura contains no anime, artwork or other media. The titles in these pictures are made up, the
posters are Kura's own placeholders and the video playing is a stand-in; where Kura's code and
notes name a real series, it's only as example data. AniList and TMDB, where Kura looks titles
up, are their owners' trademarks, and Kura isn't affiliated with or endorsed by either, nor by
any media server app. This product uses the TMDB API but is not endorsed or certified by TMDB.

## Download

From the [downloads page](https://frankgrobbelaar.github.io/kura/): Windows 10 or 11, 64-bit,
every version with what changed. Kura updates itself. It isn't code-signed, so SmartScreen warns
the first time: More info › Run anyway. The installer's first page lists everything Kura
downloads, such as ffmpeg on the first run.

### What your PC needs

Kura runs on any 64-bit Windows 10 or 11 PC. What it can convert, and how fast, depends on the
graphics card. Kura tests your PC when it's set up, says what it can and can't do there, and
measures its own times on it.

| For | It works with | Best with |
| --- | --- | --- |
| **Everything but converting** | Windows 10 or 11, 64-bit, and 8 GB of memory: finding and naming episodes, tidying up, the gap analysis and playing | 16 GB of memory |
| **Converting to the standard** | A graphics card or the processor's graphics that encodes HEVC 10-bit: NVIDIA GeForce GTX 10-series or newer, AMD Radeon RX 5000 or newer, or Intel Core 7th generation or newer | NVIDIA GeForce GTX 16-series or newer |
| **AI upscaling for SD** | A DirectX 12 graphics card. The processor's graphics work too, slowly: Kura then upscales SD the fast way unless you choose otherwise | A dedicated card with 6 GB: about an hour an episode |
| **English subtitles** | Fast: 2 GB of graphics memory, or the processor, slowly. Best: 4 GB | 6 GB: Best in about 8 minutes an episode |
| **Space** | About 350 MB for Kura and ffmpeg, 2 GB more with both speech models | Room beside your library for a converted file and its original |

Kura installs nothing by hand but a graphics driver, and says when one is too old for what it
asks of the card.

## Licence

Free software under the [MIT licence](LICENSE), with no warranty; what it's built on is listed,
each part with its licence, in `THIRD-PARTY-NOTICES.txt` with every release. Fork it freely; this
repository doesn't take contributions.
