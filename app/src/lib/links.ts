import { invoke } from "@tauri-apps/api/core";

/**
 * Opens the downloads page in the browser: every version, newest first, with what changed.
 * The shell holds the address (src-tauri/src/links.rs), so the window can't open anything else.
 */
export function openDownloadsPage() {
  return invoke<void>("open_downloads_page");
}

/** Opens TMDB's page with the account's API keys, where the key for Kura is. */
export function openTmdbApiPage() {
  return invoke<void>("open_tmdb_api_page");
}

/** Opens an anime's page on AniList, by its number there. */
export function openAniListPage(id: number) {
  return invoke<void>("open_anilist_page", { id });
}

/** Opens a show's or a film's page on TMDB, by its number there. */
export function openTmdbPage(kind: "tv" | "movie", id: number) {
  return invoke<void>("open_tmdb_page", { kind, id });
}
