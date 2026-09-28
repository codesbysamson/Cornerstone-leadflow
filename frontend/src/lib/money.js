/**
 * Money display for the CRM.
 *
 * The server is authoritative for every amount: these figures arrive as
 * already-computed strings ("300.00") and are only ever *formatted* here, never
 * recalculated. The editor's live preview is a deliberate exception and is
 * marked as such, so a staff member can see a total change as they type.
 *
 * The API returns money as JSON strings, deliberately, because JSON numbers are
 * IEEE-754 doubles in JavaScript and 0.1 + 0.2 would not survive the trip.
 */

/** Formats an amount in the quotation's own currency, e.g. £300.00. */
export function formatMoney(amount, currency = 'GBP') {
  const value = Number(amount)
  if (!Number.isFinite(value)) return '—'

  try {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    // An unrecognised code must not blank out the figure; show the bare amount
    // and let the currency code sit beside it in the UI.
    return `${value.toFixed(2)} ${currency}`
  }
}

/** A bare number for editing, e.g. "300" or "19.995". */
export function toAmountInput(amount) {
  if (amount === null || amount === undefined || amount === '') return ''
  const value = Number(amount)
  return Number.isFinite(value) ? String(amount) : ''
}

/**
 * Local preview arithmetic for the editor only.
 *
 * This runs in floating point, so it is used to give immediate feedback while
 * typing and never to decide what is saved — the server recomputes and
 * persists every figure on save. Parsing to a fixed 2-decimal representation
 * keeps the common cases clean without pretending to be authoritative.
 */
export function previewTotals(items, discount) {
  const lines = items.map((item) => {
    const quantity = Number(item.quantity)
    const unitPrice = Number(item.unit_price)
    const valid = Number.isFinite(quantity) && Number.isFinite(unitPrice)
    const total = valid ? round2(quantity * unitPrice) : 0
    return { ...item, line_total: total }
  })

  const subtotal = round2(
    lines.reduce((sum, line) => sum + line.line_total, 0),
  )
  const discountValue = Number(discount)
  const safeDiscount = Number.isFinite(discountValue) ? round2(discountValue) : 0
  const total = round2(subtotal - safeDiscount)

  return { lines, subtotal, discount: safeDiscount, total }
}

function round2(value) {
  // Half-up, matching the server, via a scaled epsilon to sidestep binary
  // representation surprises on values like 1.005.
  return Math.round((value + Number.EPSILON) * 100) / 100
}
