/**
 * Where the API lives.
 *
 * Single source of truth on purpose. This constant was previously copied into
 * three clients, and when VITE_API_BASE_URL was unset the fallback quietly
 * pointed them at `127.0.0.1` while the page was served from `localhost`. That
 * mismatch is invisible in code review and produced a bare 403 at login, so it
 * is now derived from the page itself and defined exactly once.
 */

const configured = import.meta.env.VITE_API_BASE_URL

/**
 * Defaults to the API on the *same host* as the page.
 *
 * This is not cosmetic. Cookies are scoped by host, not by port, and SameSite
 * compares host too: a `leadflow_csrf` cookie set by `127.0.0.1:8000` is
 * host-only, so a page on `localhost:5173` can neither read it via
 * `document.cookie` nor have it attached to a same-site request. Aligning the
 * hosts is what keeps both the session cookie and the CSRF cookie working.
 */
export const API_BASE_URL = (
  configured ??
  `${window.location.protocol}//${window.location.hostname}:8000`
).replace(/\/+$/, '')

/**
 * True when the API and the page are on the same host.
 *
 * When they are not, no session cookie can survive the round trip even if
 * login itself succeeds, so the app says so plainly rather than letting the
 * user meet a series of unexplained 401s.
 */
export function apiIsSameSite() {
  if (configured) {
    try {
      return new URL(configured).hostname === window.location.hostname
    } catch {
      return false
    }
  }
  return true
}
