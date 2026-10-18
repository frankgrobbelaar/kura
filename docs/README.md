# Kura docs

Short pages, one subject each. Start with the architecture, then the page for what you're touching.
Coding agents start at [AGENTS.md](../AGENTS.md); each area (`engine/`, `app/`, `app/src-tauri/`,
`docs/`) has its own `AGENTS.md` with the direction for working there.

| Page | What it covers |
| --- | --- |
| [architecture.md](architecture.md) | The three parts (shell, UI, engine), how they talk, where data lives |
| [development.md](development.md) | Setting up this PC, running Kura, checks, updating dependencies |
| [conventions.md](conventions.md) | How we write code: Python, TypeScript, Rust, tests, commits |
| [design.md](design.md) | UI and UX rules, the Cinema language and its tokens, patterns |
| [releasing.md](releasing.md) | Versions, the installer, updates, third-party notices, the signing key |
| [design/](design/) | Every screen from the design canvas, as pages you can open |
| [readme/](readme/) | The README's pictures: Kura's own screens, with made-up titles |

## The stack

Every tool Kura uses, its version on 2026-10-10, and the page that explains how Kura uses it.

| Tool | Version | Job | Page |
| --- | --- | --- | --- |
| Tauri | 2.12 | Desktop shell, window, installer, updater | [tauri.md](stack/tauri.md) |
| Rust | stable 1.99, edition 2024 | The shell's language | [tauri.md](stack/tauri.md) |
| React | 19.3 | UI components | [react.md](stack/react.md) |
| TypeScript | 7.0 | Typed UI code (the native compiler) | [react.md](stack/react.md) |
| Vite | 8.3 | Dev server and bundler for the UI | [react.md](stack/react.md) |
| React Router | 8.4 | Navigation between sections | [react.md](stack/react.md) |
| TanStack Query | 5.104 | Fetching and caching engine data | [react.md](stack/react.md) |
| Biome | 2.5 | Lint and format for the UI | [react.md](stack/react.md) |
| Tailwind CSS | 4.3 | Styling, fed by the Cinema tokens | [tailwind.md](stack/tailwind.md) |
| shadcn/ui, Radix | shadcn 4.21, radix-ui 1.8 | Accessible component starting points | [tailwind.md](stack/tailwind.md) |
| Lucide | 1.59 | Icons | [tailwind.md](stack/tailwind.md) |
| Fontsource | 5.3 | Manrope and Geist Mono, bundled for offline use | [tailwind.md](stack/tailwind.md) |
| Python | 3.14 | The engine's language | [python.md](stack/python.md) |
| uv | 0.13 | Python, packages, lockfile, running tools | [python.md](stack/python.md) |
| Ruff, Pyright | 0.17, 1.1.414 | Python lint, format and strict types | [python.md](stack/python.md) |
| FastAPI, Uvicorn, Pydantic | 0.143, 0.54, 2.14 | The engine's local API | [fastapi.md](stack/fastapi.md) |
| Typer | 0.27 | The engine's command line | [fastapi.md](stack/fastapi.md) |
| SQLite | bundled with Python | Kura's one database file | [sqlite.md](stack/sqlite.md) |
| anitopy | 2.1.1 | Reading anime file names | [anitopy.md](stack/anitopy.md) |
| ffmpeg | 9.0.2 (downloaded on first run) | Reading what each video holds, and converting it | [ffmpeg.md](stack/ffmpeg.md) |
| ONNX Runtime (DirectML), NumPy | 1.24.4, 2.5 | Running the AI upscaling model on the graphics card | [upscaling.md](stack/upscaling.md) |
| Real-ESRGAN, Anime4K | animevideov3 (v0.2.5.0), v4.0.1 | The upscaling model for SD, the shaders for 720p (ship inside Kura) | [upscaling.md](stack/upscaling.md) |
| Whisper, pyannote | medium and small (downloaded when asked for), segmentation 3.0 | English subtitles from a video's own sound, and where someone speaks (ships inside Kura) | [speech.md](stack/speech.md) |
| NVENC, AMF, Quick Sync; Windows' hardware listing | in ffmpeg's build; Windows 10 and 11 | What each PC can do: the encoder it has, the AI model, Anime4K and Whisper there, and its own times | [hardware.md](stack/hardware.md) |
| AniList | GraphQL API, no key | Which anime a file is: titles, kinds, how series connect | [anilist.md](stack/anilist.md) |
| TMDB | API v3, the owner's key | Episode lists, titles, air dates and artwork, as Plex shows them | [tmdb.md](stack/tmdb.md) |
| watchdog | 6.0 | Noticing new, removed and renamed videos in the library folders | [watchdog.md](stack/watchdog.md) |
| PyInstaller | 6.22 | Bundles the engine with its own Python | [pyinstaller.md](stack/pyinstaller.md) |
| Vitest, Testing Library, pytest | 5.0, 16.3, 9.1 | Tests | [testing.md](stack/testing.md) |
| GitHub Actions | | CI and releases | [github-actions.md](stack/github-actions.md) |
| NSIS | via Tauri | The Windows installer | [tauri.md](stack/tauri.md#installer) |

Tools planned for the build phase (ONNX Runtime) get a page when they are first used.
