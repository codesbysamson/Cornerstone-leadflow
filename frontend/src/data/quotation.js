/**
 * The quotation lifecycle, mirroring data/statuses.js for the lead pipeline.
 *
 * `value` must match the QuotationStatus values the API accepts. `tone` drives
 * the badge styling in styles/crm.css. An unrecognised stored value still
 * renders, so unexpected data is visible rather than blank.
 */
export const QUOTATION_STATUSES = [
  { value: 'DRAFT', label: 'Draft', tone: 'draft' },
  { value: 'SENT', label: 'Sent', tone: 'sent' },
  { value: 'ACCEPTED', label: 'Accepted', tone: 'accepted' },
  { value: 'REJECTED', label: 'Rejected', tone: 'rejected' },
]

const BY_VALUE = new Map(QUOTATION_STATUSES.map((s) => [s.value, s]))

export function quotationStatusMeta(value) {
  return BY_VALUE.get(value) ?? { value, label: value, tone: 'unknown' }
}

/**
 * The state machine, mirroring the server's ALLOWED_TRANSITIONS.
 *
 * Kept in step with the API deliberately: it only decides which buttons to
 * offer, and the server remains the authority that rejects anything invalid.
 */
export const QUOTATION_TRANSITIONS = {
  DRAFT: ['SENT'],
  SENT: ['ACCEPTED', 'REJECTED'],
  ACCEPTED: [],
  REJECTED: [],
}

/** Statuses reachable from the current one, for rendering actions. */
export function nextStatuses(status) {
  return QUOTATION_TRANSITIONS[status] ?? []
}

/** Only a draft can be edited; a sent quotation is a document already seen. */
export function isEditable(status) {
  return status === 'DRAFT'
}

/** Currencies offered in the editor. Any ISO 4217 code is accepted by the API;
 *  this is a convenience list for the demo, not a whitelist. */
export const CURRENCIES = [
  { code: 'GBP', label: 'GBP — Pound sterling' },
  { code: 'USD', label: 'USD — US dollar' },
  { code: 'NGN', label: 'NGN — Nigerian naira' },
  { code: 'EUR', label: 'EUR — Euro' },
]
