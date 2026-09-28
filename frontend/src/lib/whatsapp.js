/**
 * Click-to-WhatsApp.
 *
 * Provider-free: this only builds a `wa.me` deep link that opens WhatsApp with
 * a prefilled message. Nothing is sent programmatically and no messaging API,
 * token or webhook is involved — the staff member clicks, WhatsApp opens, and
 * they decide whether to send.
 *
 * The lead's `phone` is free text typed by a website visitor and is never
 * validated, so normalisation is deliberately conservative. A number is only
 * accepted when converting it to E.164 would be a mechanical, unambiguous
 * transformation. Anything else returns null and the caller renders the phone
 * as plain text, because a wrongly-routed link is worse than no link at all.
 */

/** E.164 allows at most 15 digits and never a leading zero. */
function isPlausibleE164(digits) {
  return digits.length >= 8 && digits.length <= 15 && !digits.startsWith('0')
}

/**
 * Normalises a phone number to bare E.164 digits, or returns null.
 *
 * Accepted, in order of how unambiguous the intent is:
 *   1. `00` international prefix  — 0044 7700 900123, 00234801234567
 *   2. Explicit `+` country code  — +44 7700 900123, +234 801 234 5678
 *   3. Unambiguous UK national    — 07700900123, 7700900123
 *
 * A bare local number with no `+` and no `00` is never guessed at, because
 * resolving one needs a country we cannot know. The UK national form is the
 * single exception: it is the known Apex demo format, and only the mobile
 * shape is accepted so that an arbitrary local number cannot be silently
 * relabelled as +44.
 */
export function normalisePhone(raw) {
  if (typeof raw !== 'string') return null

  const trimmed = raw.trim()
  const digits = trimmed.replace(/\D/g, '')
  if (!digits) return null

  // 00 international prefix is an explicit statement of intent.
  if (digits.startsWith('00')) {
    const international = digits.slice(2)
    return isPlausibleE164(international) ? international : null
  }

  // A leading + is an explicit country code. Covering every real country code
  // (1-3 digits) rather than a UK-only list is what keeps this international.
  if (trimmed.startsWith('+')) {
    return isPlausibleE164(digits) ? digits : null
  }

  // No international marker, so this is a local number. Only the UK mobile
  // shape is converted: 11 digits starting 07, or 10 digits starting 7.
  // Restricting on that second digit is deliberate — accepting any 11-digit
  // 0-prefixed number would relabel arbitrary local numbers as +44, and would
  // also emit links for landlines, which are rarely on WhatsApp.
  if (digits.length === 11 && digits.startsWith('07')) {
    const international = `44${digits.slice(1)}`
    return isPlausibleE164(international) ? international : null
  }
  if (digits.length === 10 && digits.startsWith('7')) {
    const international = `44${digits}`
    return isPlausibleE164(international) ? international : null
  }

  // Ambiguous local number with no country code to resolve it: refuse.
  return null
}

/**
 * A short, factual opening message for a general lead follow-up. The staff
 * member can edit it in WhatsApp before sending, so it does not try to be a
 * complete script.
 */
export function whatsappMessage(lead) {
  const parts = [
    `Hi ${lead.customer_name},`,
    'this is Apex Facility Services following up about your',
    `${lead.service} enquiry for ${lead.location}.`,
  ]
  return parts.join(' ')
}

/**
 * The quotation variant. Quotes the reference, the service and the total so the
 * customer can match the message to the document, and stays to one line.
 *
 * `formatMoney` is injected rather than imported so this module keeps its
 * single responsibility: producing the message text. The caller supplies the
 * currency-aware formatter.
 */
export function quotationWhatsappMessage(lead, quotation, formatMoney) {
  const firstName = lead.customer_name.trim().split(/\s+/)[0]
  const total = formatMoney(quotation.total, quotation.currency)

  return (
    `Hi ${firstName}, your quotation from Apex Facility Services for ` +
    `${lead.service} is ready. Reference: ${quotation.reference}. Total: ${total}.`
  )
}

/** Returns a wa.me URL, or null when the number cannot be normalised safely. */
export function buildWhatsAppUrl(lead, message) {
  const number = normalisePhone(lead.phone)
  if (!number) return null
  return `https://wa.me/${number}?text=${encodeURIComponent(message)}`
}

/** Lead follow-up link, using the default message. */
export function buildLeadWhatsAppUrl(lead) {
  return buildWhatsAppUrl(lead, whatsappMessage(lead))
}
