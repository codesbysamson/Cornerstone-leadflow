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

/**
 * Formats an ISO timestamp for an `input[type="datetime-local"]` control,
 * which needs `YYYY-MM-DDTHH:mm` in the viewer's local time.
 *
 * Returns an empty string for an unset or unparseable value, so a follow-up
 * that is being set for the first time opens on a blank control while a
 * reschedule opens pre-filled with the value already stored.
 */
export function toLocalInputValue(value) {
  const date = toDate(value)
  if (!date) return ''

  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/**
 * Converts a `datetime-local` control's local wall-clock value into an
 * unambiguous UTC ISO string for the API.
 *
 * This step is required, not cosmetic. A naive value would be written to a
 * TIMESTAMPTZ column and silently interpreted in the database server's zone;
 * the API rejects naive input, so the offset has to be attached here.
 */
export function toUtcIso(localValue) {
  if (!localValue) return null
  const date = new Date(localValue)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}
