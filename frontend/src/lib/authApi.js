/**
 * Staff authentication client.
 *
 * Session state lives entirely in cookies: `leadflow_session` is HttpOnly and
 * unreadable by script, `leadflow_csrf` is deliberately readable because the
 * frontend has to copy it into a request header. There is no token in
 * JavaScript, in localStorage, or in the URL — so an XSS cannot lift a session
 * and reuse it elsewhere, and a session does not survive in a shared link.
 *
 * This is separate from lib/api.js, which serves the public website and must
 * never send credentials.
 */

import { API_BASE_URL, apiIsSameSite } from './apiConfig.js'

export const AUTH_ENDPOINT = `${API_BASE_URL}/api/auth`

/** The state-changing methods that must carry the CSRF header. */
const STATE_CHANGING = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

/**
 * The CSRF token the server issued, as last reported by the session probe.
 *
 * Held in memory only. It is never written to localStorage or sessionStorage:
 * a token persisted in storage outlives the tab and is readable by any injected
 * script, which is exactly what the HttpOnly session cookie exists to prevent.
 * A page reload simply re-probes and gets a fresh one.
 */
let probeCsrfToken = null

/**
 * The CSRF token to send.
 *
 * The cookie wins when it is readable, because it is always the freshest value
 * and stays correct when a second tab logs in. The probe's token is the
 * fallback for when the cookie is *not* readable — the cookie is host-only, so
 * a page on a different host than the API cannot see it in `document.cookie`.
 */
export function readCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)leadflow_csrf=([^;]*)/)
  if (match) return decodeURIComponent(match[1])
  return probeCsrfToken
}

/**
 * The headers and options every staff request needs.
 *
 * `credentials: 'include'` is what actually sends the session cookie; without
 * it the browser omits the cookie and every request is a 401. The CSRF header
 * is only added for writes, because reads do not require one.
 */
export function staffRequestOptions(method, extraHeaders = {}) {
  const headers = { ...extraHeaders }

  if (STATE_CHANGING.has(method.toUpperCase())) {
    const token = readCsrfToken()
    if (token) headers['X-CSRF-Token'] = token
  }

  return { headers, credentials: 'include' }
}

const REQUEST_FAILED =
  'Could not reach the LeadFlow API. Check that the backend is running and try again.'

async function parse(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export class SessionExpiredError extends Error {
  constructor() {
    super('Your session has ended. Please sign in again.')
    this.name = 'SessionExpiredError'
    this.status = 401
  }
}

/**
 * Asks the API whether the browser holds a valid staff session.
 *
 * This is also what mints the CSRF cookie, so it is always called before the
 * first login attempt. It never throws for an ordinary "not signed in" — that
 * is a successful answer with `authenticated: false` — so the app can branch on
 * one shape instead of treating normal state as an error.
 */
export async function probeSession() {
  let response

  try {
    response = await fetch(`${AUTH_ENDPOINT}/session`, {
      method: 'GET',
      credentials: 'include',
    })
  } catch {
    throw new Error(REQUEST_FAILED)
  }

  const body = await parse(response)

  if (!response.ok || !body) {
    throw new Error(REQUEST_FAILED)
  }

  if (typeof body.csrf_token === 'string' && body.csrf_token) {
    probeCsrfToken = body.csrf_token
  }

  return body
}

/**
 * The message shown when the API is on a different host than the page.
 *
 * Login can still be attempted and will succeed, but the session cookie is
 * host-only and would never come back, so the CRM would then be a wall of 401s.
 * Saying this once, clearly, is far more useful than that.
 */
export function crossSiteWarning() {
  return apiIsSameSite()
    ? null
    : `The API (${API_BASE_URL}) and this page (${window.location.origin}) are on ` +
        'different hosts, so the session cookie cannot be sent. Point ' +
        'VITE_API_BASE_URL at the same host as the page.'
}

/**
 * Exchanges credentials for a session cookie.
 *
 * Requires the CSRF cookie, so `probeSession()` must have run first. Errors are
 * deliberately not distinguished here: the API returns one generic message for
 * every failure, and this passes it straight through rather than inventing a
 * more specific one that would leak whether the account exists.
 */
export async function login(email, password) {
  let response

  try {
    response = await fetch(`${AUTH_ENDPOINT}/login`, {
      method: 'POST',
      ...staffRequestOptions('POST', { 'Content-Type': 'application/json' }),
      body: JSON.stringify({ email, password }),
    })
  } catch {
    throw new Error(REQUEST_FAILED)
  }

  if (response.status === 401) {
    throw new Error('Invalid email or password.')
  }

  if (!response.ok) {
    throw new Error('Sign in failed. Please try again in a moment.')
  }

  const user = await parse(response)

  // Login issues a new CSRF token and a new cookie. The token captured before
  // login no longer matches, so it is discarded here and re-read by the probe
  // below; without this every write after sign-in would be rejected with 403.
  probeCsrfToken = null
  await probeSession()

  return user ?? { email, display_name: null }
}

/** Revokes the server-side session. Failure is reported but not fatal. */
export async function logout() {
  try {
    await fetch(`${AUTH_ENDPOINT}/logout`, {
      method: 'POST',
      ...staffRequestOptions('POST'),
    })
  } catch {
    // The cookie is cleared by the server's Set-Cookie. If the network failed
    // it may survive, so the caller still has to drop its in-memory state.
  } finally {
    probeCsrfToken = null
  }
}
