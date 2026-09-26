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
const REQUEST_FAILED_STATUS =
  'The status could not be updated. Nothing was changed — please try again.'

async function request(path, options = {}) {
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
    throw new Error(REQUEST_FAILED_STATUS)
  }

  return body
}

export async function listLeads() {
  return request(LEADS_ENDPOINT, { method: 'GET' })
}

export async function updateLeadStatus(leadId, status) {
  return request(`${LEADS_ENDPOINT}/${leadId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}
