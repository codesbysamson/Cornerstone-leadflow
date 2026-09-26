/**
 * LeadFlow API client.
 *
 * The base URL comes from VITE_API_BASE_URL at build time. Internal detail
 * (status codes, response bodies, exception text) is never surfaced to the
 * user — callers only receive a safe, human-readable message.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

export const LEAD_ENDPOINT = `${API_BASE_URL}/api/leads`

/** Maps a 422 FastAPI validation payload to "field: message" pairs. */
function readValidationDetail(body) {
  if (!Array.isArray(body?.detail)) return {}

  return body.detail.reduce((acc, item) => {
    const field = item?.loc?.at(-1)
    if (typeof field === 'string' && !acc[field]) {
      acc[field] = 'Please check this field.'
    }
    return acc
  }, {})
}

export async function createLead(lead) {
  let response

  try {
    response = await fetch(LEAD_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lead),
    })
  } catch {
    throw new Error(
      'We could not reach the Apex service. Check that the API is running and try again.',
    )
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (response.status === 422) {
    const error = new Error(
      'Some details were not accepted. Please review the form and try again.',
    )
    error.fields = readValidationDetail(body)
    throw error
  }

  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error(
        'Something went wrong on our side. Your request has not been lost — please try again.',
      )
    }
    throw new Error(
      'Your request could not be submitted. Please try again in a moment.',
    )
  }

  return body
}
