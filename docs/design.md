# Design

How Kura looks and behaves. The look is **Cinema**, chosen by the owner from three directions
(the [options record](design/options.html) keeps the other two), and its light mode is **Paper**,
chosen from three lights in the
[Kura Light Mode Options canvas](https://claude.ai/artifact/7Bdz7CoKjBbV8JrSLXfu4y). Every screen is
drawn in the [Kura Workflows canvas](https://claude.ai/artifact/XgGkfpW6doBUPcnrPqrbxb); snapshots
you can open locally are in [design/](design/README.md). Build to those boards, and never change
the look unasked.

## The bar

Simple to use and beautiful, like Revolut or Linear: fewer, clearer elements and one strong
primary action per view. Smooth motion that explains what changed. Simple charts and honest
progress. And no struggling with small things: every error, empty state and recovery is designed.

## Eight rules every screen follows

1. **Status reads without colour.** Shape and label carry the meaning; colour reinforces it.
   Ready is a solid amber square, converting pulses, to convert is solid blue, broken is hatched
   red, missing is a hollow ring. Amber and blue also differ in lightness.
2. **Motion explains, never decorates.** Hover and press 120 ms, toggles and chips 200 ms, panels
   and pages 320 ms, charts on first view 600 to 900 ms. One curve, `cubic-bezier(.2,.8,.2,1)`:
   a quick start and a soft landing. With Windows' animation effects off, nothing moves.
3. **Charts stay simple.** Label the data, not an axis. One accent per chart, neutral grey for the
   rest. No 3D, no gradients, no dual axes.
4. **Progress says what, how far and how long.** Every long job shows its stage, a percentage and
   the time left, and can be paused. Nothing spins silently.
5. **Nothing changes until you review it.** Renames, moves, deletions and conversions are proposed
   as a before and after, applied on approval, logged, and undoable. Duplicates go to quarantine.
6. **Fits every window size.** Compact under 900 px, standard 900 to 1440, wide above. Layouts
   reflow on their own: the nav rail folds into a row on top, panels stack, grids change columns.
   Only the page scrolls: the nav rail and the page's top (`page-top`: its title or breadcrumb)
   stay where they are. The one exception is the Library's Coming up, a strip that scrolls
   sideways through the days, as the owner asked.
7. **Light and dark, designed together.** Dark is Cinema; light is Paper: a warm paper ground,
   cream panels that lift with a soft shadow, ink text, the same amber. Kura is light or dark as
   Windows is, unless the owner picks one in Settings › General. Body text keeps 4.5:1 contrast in
   both, and status keeps its shapes (on paper, a ready square gets a darker edge). The featured
   panel stays blue, and a part that must stay dark, such as a video, says so (`scheme-dark`).
8. **Keyboard first, mouse friendly.** Everything can be reached and done from the keyboard, the
   focus ring is always visible, and click targets are at least 40 px. Two shortcuts where they
   pay off: Space pauses the queue, and 1 to 3 picks a guess on "Which anime is this?". No others
   are planned (the owner, 2026-10-14).

## Cinema in code

The tokens live in [app/src/styles/tokens.css](../app/src/styles/tokens.css); Tailwind turns them
into classes, and Tailwind's own palette is switched off so nothing off-system creeps in. A colour
that differs in light mode is written `light-dark(paper, cinema)`, so one class serves both.

| For | Use | Dark (Cinema) | Light (Paper) |
| --- | --- | --- | --- |
| The window | `bg-window` | #0b0c0f | #f3efe6 |
| A panel | `bg-glass border border-edge rounded-22 shadow-panel` | white at 4%, border white at 8% | #fffcf6, border #e6dfd1, soft shadow |
| A dialog | `bg-dialog rounded-28 shadow-dialog` | #121419 | #fffcf6 |
| Main text, secondary, footnotes | `text-fg`, `text-fg-muted`, `text-fg-faint` | #f4f5f7, #a3a8b3, #7c818c | #1d1912, #5d564a, #6e6759 |
| Labels and inactive controls | `text-fg-soft` | #d7dae0 | #34302a |
| The primary action | `bg-accent text-on-accent` | #f2b33d on #1d1300 | the same |
| Amber text, selected state | `text-accent-fg`, `bg-accent/12` | #ffd27a, amber at 12% | #7f5200, amber at 12% |
| A secondary button or a field | `bg-field border border-field-edge` | white at 5%, border white at 12% | #fffcf6, border #dcd3c2 |
| Behind segmented choices and tabs | `bg-well` | white at 5% | #ebe4d6 |
| Lines between rows | `border-rule` | white at 6% | #eee7da |
| A chip, a tag, a hover, a box inside a panel | `bg-tint/6` (and /3 to /12) | white at that share | ink at that share |
| A tag on artwork | `bg-tag` | the window at 60% | cream at 90% |
| Status swatches | `status-ready`, `status-converting`, `status-convert`, `status-broken`, `status-missing` | solid, pulsing, blue, hatched, hollow | the same, ready with a darker edge |
| The featured panel | `bg-featured` with `bg-featured-orb`, `scheme-dark` | #13254f, #f08a24 | the same |
| Paths, sizes, times | `font-mono` | Geist Mono |
| Headings | `type-title` (32), `type-heading` (20), `type-display` (50) | Manrope 800 |
| Other text | `text-14` (body), `text-13`, `text-12`, `text-11` | px-named sizes |
| Corners | `rounded-14` to `rounded-24` panels, `rounded-full` buttons and chips | |
| Motion | `ease-cinema`, `duration-120`/`200`/`320`, `animate-fade-up`, `press`, `lift` | |

Rules of thumb:

- One `bg-accent` button per view; everything else is secondary (a field with a border) or ghost.
- Text on amber is always `text-on-accent`; amber text is `text-accent-fg`, never `text-accent`.
- Artwork brings the colour. The interface stays near-black in dark and warm paper in light, with
  one warm accent; colours from posters and mock artwork are not UI tokens.
- No `white/…` or `black/…` on the interface: they don't turn with light mode. Use `tint`, `rule`,
  `field` and `well`. White and black are for what sits on artwork, and for what stays dark: a
  part that must (the featured panel, a video) carries `scheme-dark`, and its tokens resolve dark.
- If a value you need isn't a token, it isn't Cinema yet. Ask before adding one, with its value in
  both lights.

## Components

Built so far, in `app/src/components/`:

| Component | Use it for |
| --- | --- |
| `ui/button.tsx` | Every button. Variants `primary`, `secondary`, `ghost`, `danger`; sizes `md` (44 px) and `sm` (36 px); `asChild` to style a link |
| `empty-state.tsx` | A place with nothing in it yet, with its one next step |
| `shell/` | The title bar, nav rail, update card and the notes at the window's foot (offline, what the engine tells of) around every screen |
| `kura-logo.tsx` | The mark |
| `tmdb-credit.tsx` | TMDB's credit line with its logo, as its terms ask |

New primitives start from shadcn/ui (accessible, built on Radix) and are restyled to Cinema; see
[stack/tailwind.md](stack/tailwind.md). The boards show the rest to build: radio cards, switches,
segmented controls, chips, progress bars and rings, the episode map, poster cards, review lists
(before → after), toasts with Undo, and dialogs.

## Patterns from the boards

- **Page header**: `type-title`, a one-line summary under it in `text-fg-muted`, the page's primary
  action on the right.
- **A long job**: stage steps (done, current pulsing, next hollow), a bar or ring with the
  percentage, and "18 min left". Pause is always there.
- **Review before apply**: the proposed change as old name → new name in Geist Mono, grouped, with
  counts; "Apply 30 changes" as the one primary button; Undo afterwards in a toast and in History.
- **The small things** (board 5.3): a drive unplugged, not enough space, a file in use, a crash,
  a failed conversion, a name already taken, offline, a name Windows can't use. Each message names
  the problem, says what Kura already did, and offers the next step.

## Words

- Plain words, short sentences, second person: "Your shelf is empty".
- Say what happens: "Kura closes, updates and opens again", not "Applying update".
- Numbers carry their units and stay human: "18 min left", "≈ 450 MB per episode", "today 14:20".
- No exclamation marks, no blame, no jargon (say "picture" and "sound", not "video stream").
