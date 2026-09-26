/**
 * Date and value formatting shared by the CRM views.
 *
 * The API returns ISO-8601. Against PostgreSQL the timestamp carries a UTC
 * offset; the SQLite test database returns a naive value, so parsing is
 * defensive and an unparseable value degrades to an em dash rather than
 * rendering "Invalid Date".
 */

const EM_DASH = '—'

function toDate(value) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatDate(value) {
  const date = toDate(value)
  if (!date) return EM_DASH
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function formatDateTime(value) {
  const date = toDate(value)
  if (!date) return EM_DASH
  return date.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Renders an optional enquiry field, or a muted placeholder. */
export function orDash(value) {
  return value === null || value === undefined || value === '' ? EM_DASH : value
}
