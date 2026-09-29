/**
 * Quotation API client for the staff CRM.
 *
 * Kept separate from lib/api.js (the customer quote request) and alongside
 * lib/crmApi.js, which holds the lead-side calls.
 *
 * Money is sent as strings and received as strings: the API persists Decimal
 * and serialises amounts as JSON strings, because JSON numbers cannot represent
 * decimal money exactly.
 *
 * Like crmApi.js, every call is credentialed: quotations are staff-only, so the
 * session cookie and the CSRF header come from authApi.js. The public quote
 * request in lib/api.js is unaffected and sends neither.
 */

import { API_BASE_URL } from './apiConfig.js'
import { SessionExpiredError, staffRequestOptions } from './authApi.js'

export const API_ROOT = `${API_BASE_URL}/api`

const REQUEST_FAILED =
  'Could not reach the LeadFlow API. Check that the backend is running and try again.'

async function request(path, failureMessage, method, payload) {
  const writes = method !== 'GET'

  let response

  try {
    // Session cookie, CSRF header and JSON body are all attached here, so no
    // individual call can forget any of them.
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
    // Distinguished so an expired session returns to the sign-in screen rather
    // than showing a misleading quotation error.
    throw new SessionExpiredError()
  }

  if (response.status === 403) {
    throw new Error('Your session has expired. Please sign in again.')
  }

  if (response.status === 404) {
    throw new Error(body?.detail ?? 'That record no longer exists.')
  }

  if (response.status === 409) {
    // A state-machine rejection carries an explanation worth showing verbatim.
    throw new Error(body?.detail ?? 'That action is not allowed.')
  }

  if (!response.ok) {
    throw new Error(failureMessage)
  }

  return body
}

/** Serialises the editor state. Totals are deliberately not sent. */
function quotationBody(draft) {
  return {
    currency: draft.currency,
    discount: draft.discount === '' ? '0' : draft.discount,
    notes: draft.notes === '' ? null : draft.notes,
    items: draft.items.map((item) => ({
      description: item.description,
      quantity: item.quantity === '' ? '0' : item.quantity,
      unit_price: item.unit_price === '' ? '0' : item.unit_price,
    })),
  }
}

export async function listQuotations(leadId) {
  return request(
    `${API_ROOT}/leads/${leadId}/quotations`,
    'The quotations could not be loaded.',
    'GET',
  )
}

export async function getQuotation(quotationId) {
  return request(
    `${API_ROOT}/quotations/${quotationId}`,
    'The quotation could not be loaded.',
    'GET',
  )
}

export async function createQuotation(leadId, draft) {
  return request(
    `${API_ROOT}/leads/${leadId}/quotations`,
    'The quotation could not be created.',
    'POST',
    quotationBody(draft),
  )
}

export async function updateQuotation(quotationId, draft) {
  return request(
    `${API_ROOT}/quotations/${quotationId}/update`,
    'The draft could not be saved. Your changes were not applied.',
    'POST',
    quotationBody(draft),
  )
}

export async function transitionQuotation(quotationId, status) {
  return request(
    `${API_ROOT}/quotations/${quotationId}/status`,
    'The status could not be changed. Nothing was updated.',
    'POST',
    { status },
  )
}
