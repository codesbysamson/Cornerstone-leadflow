/**
 * Staff CRM API client.
 *
 * Deliberately separate from lib/api.js: the customer-facing client uses
 * Apex-voiced error copy, and staff tooling needs its own phrasing. Keeping
 * them apart means the public demo copy cannot be affected by CRM changes.
 *
 * The base URL comes from VITE_API_BASE_URL at build time.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

export const LEADS_ENDPOINT = `${API_BASE_URL}/api/leads`

const REQUEST_FAILED =
  'Could not reach the LeadFlow API. Check that the backend is running and try again.'

/**
 * The shared request helper. `failureMessage` is supplied per call because a
 * single generic string would mislabel what actually failed — "the status
 * could not be updated" is wrong and alarming when it was a note that failed.
 */
async function request(path, failureMessage, options = {}) {
  let response

  try {
    response = await fetch(path, options)
  } catch {
    throw new Error(REQUEST_FAILED)
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (response.status === 404) {
    throw new Error(body?.detail ?? 'That lead no longer exists.')
  }

  if (!response.ok) {
    throw new Error(failureMessage)
  }

  return body
}

function jsonBody(payload) {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

export async function listLeads() {
  return request(`${LEADS_ENDPOINT}`, 'The leads could not be loaded.', {
    method: 'GET',
  })
}

export async function updateLeadStatus(leadId, status) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/status`,
    'The status could not be updated. Nothing was changed — please try again.',
    { method: 'POST', ...jsonBody({ status }) },
  )
}

export async function listNotes(leadId) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/notes`,
    'The activity history could not be loaded.',
    { method: 'GET' },
  )
}

export async function createNote(leadId, body) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/notes`,
    'The note could not be saved. Please try again.',
    { method: 'POST', ...jsonBody({ body }) },
  )
}

/** Sets or reschedules the follow-up. Reschedule is just a second call. */
export async function saveFollowUp(leadId, dueAt, action) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/follow-up`,
    'The follow-up could not be saved. Nothing was changed — please try again.',
    { method: 'POST', ...jsonBody({ due_at: dueAt, action }) },
  )
}

export async function clearFollowUp(leadId) {
  return request(
    `${LEADS_ENDPOINT}/${leadId}/follow-up`,
    'The follow-up could not be cleared. Nothing was changed — please try again.',
    { method: 'POST', ...jsonBody({ clear: true }) },
  )
}
