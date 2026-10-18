# App UI: guide for coding agents

The UI lives in `app/src`: React 19, TypeScript 7, Tailwind 4, built by Vite. The Rust shell in
`app/src-tauri` has [its own guide](src-tauri/AGENTS.md). Start with [../AGENTS.md](../AGENTS.md)
and [../CLAUDE.md](../CLAUDE.md).

## Build to the design

- Every screen has a board in `docs/design/screens/`. Match it: layout, spacing, copy, states.
  Its inline values map one to one to the tokens in `src/styles/tokens.css`.
- Use only Cinema tokens. Tailwind's own palette and scales are switched off on purpose; if a
  value isn't a token, ask the owner before adding one.
- Light and dark come from the same classes: every colour token holds both (`light-dark()`), and
  the page follows the window's theme. So no `white/…` or `black/…` on the interface (`bg-tint/6`,
  `border-rule`, `bg-field`, `bg-well` instead; see [design.md](../docs/design.md)); white and black
  only on artwork, and in a part that stays dark, which carries `scheme-dark`. Check a new screen
  in both: `color-scheme: light` on `<html>` shows it light.
- One primary (amber) action per view; the rest are secondary or ghost buttons.
- Every screen designs its loading, empty and error states, following the "small things" board:
  name the problem, say what Kura did, offer the next step.
- Motion: `ease-cinema`, 120 / 200 / 320 ms, `animate-fade-up` for entrances. Reduced motion is
  handled globally; don't work around it.
- Accessible as built: real `<button>` and `<a>`, labels on icon-only buttons, visible focus, a
  keyboard path for everything, `role="alert"` or `role="status"` for messages that appear.
- Only the page scrolls. A page starts with its top, its header or a breadcrumb, carrying
  `page-top`, so it stays put while the rest scrolls under it.
- Say what a thing does, never which media server reads it: no "Plex" anywhere in the UI.
- Markdown (Kura's reports) shows through `components/markdown.tsx`, as a reader sees it.
- More about one thing, a title the library lacks say, opens in a side sheet
  (`components/ui/sheet.tsx`): from the window's right, below the title bar, the page dimming
  behind it, closed by Escape, its cross or a click beside it. A synopsis, genres, facts and
  "On AniList" / "On TMDB" come from `components/about.tsx`; the shell opens those pages by
  number (`lib/links.ts`), as the window can't open addresses itself. Panels with a heading are
  `components/panel.tsx`.
- Wherever a video file shows, its row's "More" menu (`components/ui/menu.tsx`, Radix's dropdown)
  has "Show in folder" and "Copy path" (`components/file-actions.tsx`), with a line under the row
  saying how that went; deleting sits last, apart, as "Delete…". A title's videos and episodes
  open in full in a side sheet (`features/title/video-sheet.tsx`), what happens in an episode
  hidden till asked, as it gives the story away.
- Lists of titles group them by type, series, movies, OVAs then specials (`KIND_ORDER` in
  `lib/kinds.ts`), through `components/title-groups.tsx`, except in the orders that look across
  types ("Recently added", "Most missing").
- A list that grows long has a search (`components/search-field.tsx`), shown once there's more
  than one thing in it: it narrows the list as you type, wanting every word however it's written
  (`lib/search.ts`), keeps to the page's address (`?q=`) so going back finds it, and says when
  nothing goes by it. What it hides isn't acted on: Tidy up applies, and the queue's ticks move,
  only what's found. History's filter asks the engine (`useHistory(query)`), as History comes a
  few days at a time.
- The title bar's search (`components/shell/library-search.tsx`, as the boards draw it, without
  their Ctrl K) asks the engine (`useSearch`) once the owner stops typing and lists the anime,
  episodes and videos it finds under the field: arrow keys and Enter, or a click, open one, once
  the list answers what's typed. An episode or a video opens its title's page searched for it
  (`?q=`, with `state.videos`, which takes the page down to its videos); a video Kura files under
  no title, an extra, shows in its folder.
- Deleting asks first, beside what goes (`components/delete.tsx`, on a title's page and on "Which
  anime is this?"), says where it goes and for how long, and offers it back right after. Nothing
  is ever deleted outright; emptying a drive's quarantine early to make room
  (`features/convert/no-room.tsx`) asks once more and says it can't come back, and choosing to
  delete converted files' originals (Convert, Settings) says the same where it's chosen.
- While Kura's records are damaged, the way back (`features/records/`) stands in for every page
  (`components/shell/app-shell.tsx`): the engine answers nothing else.
- A video plays in the player over whichever page is open (`features/player/`, its provider in
  the shell): a page offers Play with `usePlayer().play(items, index, from)`, the videos after
  `index` playing next. Its `<video>` plays the engine's stream address (`streamAddress` in
  `lib/engine.tsx`), which carries the video's ticket instead of the token. The player stays
  dark in light mode (`scheme-dark`), as a picture does. A `PlayItem`'s `resume` is where the
  video stopped last time: Play picks it up there unless `from` says otherwise, and the player
  tells the engine where it is as it plays (`usePositionNote`), a look of a few seconds aside.
- English subtitles are asked for on their own page (`features/subtitles/make-page.tsx`, at
  `/subtitles?title=7&season=1`, or `/subtitles` for everything without English): a title's
  videos and Home's card lead there. Whatever Kura made from the sound says so where it shows
  (the title's videos, the player's menu, History), since names and jokes can come out wrong.
- Tidy up's copies panel offers the other copy's English when it has some the kept one hasn't
  (`features/tidy/tidy-page.tsx`): with it, the other copy's changes stay out of what's applied
  and the kept copy's path goes in `english`; the queue adds the English, then sets both aside.

## Where things go

| What | Where |
| --- | --- |
| A screen and its parts | `src/features/<area>/` (`home/`, then `tidy/`, `convert/`, …) |
| Shared primitives (buttons, switches, dialogs…) | `src/components/ui/` |
| The window frame (title bar, nav rail, update card, the notes at its foot) | `src/components/shell/` |
| Talking to the engine and the shell | `src/lib/engine.tsx`, `src/lib/updates.ts` |
| Tokens and global styles | `src/styles/` |
| Routes | `src/app.tsx`; nav items, and the one a new page lights (`sectionOf`), in `src/components/shell/sections.ts` |

## Data

- Engine data comes only through `src/lib/engine.tsx`: add a typed hook per endpoint
  (`export const useLibrary = () => useEngineQuery<Library>("/library")`), with its type mirroring
  `engine/openapi.json`. Changes use `useMutation` and invalidate the queries they affect.
- No `fetch` or `invoke` outside `src/lib/`.
- Local state stays in components. Add a global store only when two distant screens truly share
  client-side state.

## Components

- Reuse what exists (`Button`, `EmptyState`, and `EngineProblem` for a screen whose data didn't
  come) before adding anything.
- New primitives start from shadcn/ui (`pnpm dlx shadcn@latest add <name>`) and are restyled to
  Cinema with the mapping in [docs/stack/tailwind.md](../docs/stack/tailwind.md). They live in
  `src/components/ui/` and open with a comment naming shadcn/ui and `LICENSE-shadcn.txt`.
- A new npm package needs a licence on the allowed list in
  `engine/tools/third_party_notices.py`; `pnpm build:installer` stops otherwise.
- Merge classes with `cn()`. New font sizes or radii also go in `fontSizes` and `radii` in
  `src/lib/utils.ts` (a test checks).
- Icons from `lucide-react`; decorative ones get `aria-hidden="true"`.

## Commands

```powershell
pnpm tauri dev      # run Kura (UI with hot reload, shell, engine)
pnpm check          # Biome, TypeScript, Vitest
pnpm fix            # format and apply safe lint fixes
pnpm test:watch     # tests while you work
```

## Done means

`pnpm check` and `pnpm build` are green; the screen matches its board and works in the running app
with its loading, empty and error states; tests cover what a person sees and does. Guides:
[react.md](../docs/stack/react.md), [tailwind.md](../docs/stack/tailwind.md),
[design.md](../docs/design.md), [testing.md](../docs/stack/testing.md).
