/**
 * Staff CRM API client.
 *
 * Deliberately separate from lib/api.js: the customer-facing client uses
 * Apex-voiced error copy, and staff tooling needs its own phrasing. Keeping
 * them apart means the public demo copy cannot be affected by CRM changes.
 *
 * The base URL comes from VITE_API_BASE_URL at build time.
 *
 * Every call is credentialed: the staff session is a cookie, so
 * `credentials: 'include'` and the CSRF header come from authApi.js. This is
 * kept strictly separate from lib/api.js, which serves the public website and
 * must never send credentials — a customer submitting an enquiry has no
 * session, and the endpoint does not want one.
 */

import { API_BASE_URL } from './apiConfig.js'
import { SessionExpiredError, staffRequestOptions } from './authApi.js'

export const LEADS_ENDPOINT = `${API_BASE_URL}/api/leads`

const REQUEST_FAILED =
  'Could not reach the LeadFlow API. Check that the backend is running and try again.'

/**
 * The shared request helper. `failureMessage` is supplied per call because a
 * single generic string would mislabel what actually failed — "the status
 * could not be updated" is wrong and alarming when it was a note that failed.
 */
async function request(path, failureMessage, method, payload) {
  const writes = method !== 'GET'

  let response

  try {
    // The session cookie, the CSRF header and the JSON body are all built here,
    // so no individual call can forget any of them.
    response = await fetch(path, {
      ...staffRequestOptions(method, writes ? { 'Content-Type': 'application/json' } : {}),
      method,
      ...(writes ? { body: JSON.stringify(payload) } : {}),
    })
  } catch {
    throw new Error(REQUEST_FAILED)
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (response.status === 401) {
    // The session expired mid-use. Surfaced distinctly so the app can return
    // to the sign-in screen rather than showing a generic failure.
    throw new SessionExpiredError()
  }

  if (response.status === 403) {
    // Only reachable if the CSRF token is stale, which the session probe fixes.
    throw new Error('Your session has expired. Please sign in again.')
  }

  if (response.status === 404) {
    throw new Error(body?.detail ?? 'That lead no longer exists.')
  }

  if (!response.ok) {
    throw new Error(failureMessage)
  }

  return body
}

export async function listLeads() {
  return request(`${LEADS_ENDPOINT}`, 'The leads could not be loaded.', 'GET')
}

export async function updateLeadStatus(leadId, status) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/status`,
    'The status could not be updated. Nothing was changed — please try again.',
    'POST',
    { status },
  )
}

export async function listNotes(leadId) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/notes`,
    'The activity history could not be loaded.',
    'GET',
  )
}

export async function createNote(leadId, body) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/notes`,
    'The note could not be saved. Please try again.',
    'POST',
    { body },
  )
}

/** Sets or reschedules the follow-up. Reschedule is just a second call. */
export async function saveFollowUp(leadId, dueAt, action) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/follow-up`,
    'The follow-up could not be saved. Nothing was changed — please try again.',
    'POST',
    { due_at: dueAt, action },
  )
}

export async function clearFollowUp(leadId) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/follow-up`,
    'The follow-up could not be cleared. Nothing was changed — please try again.',
    'POST',
    { clear: true },
  )
}
