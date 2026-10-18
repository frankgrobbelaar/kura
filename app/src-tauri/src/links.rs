//! Pages Kura opens in the browser. The window can't open addresses itself: it asks for one of
//! these by name, so it can never be steered anywhere else.

use tauri::AppHandle;
use tauri_plugin_opener::OpenerExt;

/// Every released version, newest first, with what changed and its installer.
/// Built by scripts/downloads-page.mjs; see docs/releasing.md.
pub const DOWNLOADS_PAGE: &str = "https://frankgrobbelaar.github.io/kura/";

/// Where a TMDB account's keys are, for the TMDB key in Setup.
pub const TMDB_API_PAGE: &str = "https://www.themoviedb.org/settings/api";

/// Opens the downloads page in the default browser.
#[tauri::command]
pub fn open_downloads_page(app: AppHandle) -> Result<(), String> {
    open(&app, DOWNLOADS_PAGE)
}

/// Opens TMDB's page with the account's API keys in the default browser.
#[tauri::command]
pub fn open_tmdb_api_page(app: AppHandle) -> Result<(), String> {
    open(&app, TMDB_API_PAGE)
}

/// Opens an anime's page on AniList, by its number there, in the default browser.
#[tauri::command]
pub fn open_anilist_page(app: AppHandle, id: u64) -> Result<(), String> {
    open(&app, &anilist_page(id))
}

/// Opens a show's or a film's page on TMDB ("tv" or "movie"), by its number there.
#[tauri::command]
pub fn open_tmdb_page(app: AppHandle, kind: String, id: u64) -> Result<(), String> {
    open(&app, &tmdb_page(&kind, id)?)
}

/// An anime's page on AniList: only a number goes into it.
fn anilist_page(id: u64) -> String {
    format!("https://anilist.co/anime/{id}")
}

/// A show's or a film's page on TMDB: only its kind, one of two words, and a number go in.
fn tmdb_page(kind: &str, id: u64) -> Result<String, String> {
    match kind {
        "tv" | "movie" => Ok(format!("https://www.themoviedb.org/{kind}/{id}")),
        _ => Err(format!("TMDB has no pages of kind {kind:?}")),
    }
}

fn open(app: &AppHandle, address: &str) -> Result<(), String> {
    app.opener()
        .open_url(address, None::<&str>)
        .map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{DOWNLOADS_PAGE, TMDB_API_PAGE, anilist_page, tmdb_page};

    #[test]
    fn the_downloads_page_is_kuras_own_secure_site() {
        assert!(DOWNLOADS_PAGE.starts_with("https://frankgrobbelaar.github.io/kura"));
    }

    #[test]
    fn the_tmdb_page_is_tmdbs_own_secure_site() {
        assert!(TMDB_API_PAGE.starts_with("https://www.themoviedb.org/"));
    }

    #[test]
    fn an_anime_opens_on_anilist_by_its_number() {
        assert_eq!(anilist_page(813), "https://anilist.co/anime/813");
    }

    #[test]
    fn a_show_or_film_opens_on_tmdb_and_nothing_else_does() {
        assert_eq!(
            tmdb_page("tv", 12971).as_deref(),
            Ok("https://www.themoviedb.org/tv/12971")
        );
        assert_eq!(
            tmdb_page("movie", 11299).as_deref(),
            Ok("https://www.themoviedb.org/movie/11299")
        );
        assert!(tmdb_page("../settings", 1).is_err());
    }
}
