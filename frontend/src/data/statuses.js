/**
 * The LeadFlow pipeline.
 *
 * `value` must match the LeadStatus values accepted by the API. `tone` drives
 * the badge styling in styles/crm.css. Order is pipeline order, used for the
 * dashboard sequence and the status control.
 */
export const LEAD_STATUSES = [
  { value: 'NEW', label: 'New', tone: 'new' },
  { value: 'CONTACTED', label: 'Contacted', tone: 'contacted' },
  { value: 'QUALIFIED', label: 'Qualified', tone: 'qualified' },
  { value: 'QUOTE_SENT', label: 'Quote Sent', tone: 'quote-sent' },
  { value: 'WON', label: 'Won', tone: 'won' },
  { value: 'LOST', label: 'Lost', tone: 'lost' },
]

export const STATUS_VALUES = LEAD_STATUSES.map((status) => status.value)

const BY_VALUE = new Map(LEAD_STATUSES.map((status) => [status.value, status]))

/** Falls back to a neutral badge if the API ever returns an unknown value. */
export function statusMeta(value) {
  return BY_VALUE.get(value) ?? { value, label: value, tone: 'unknown' }
}
