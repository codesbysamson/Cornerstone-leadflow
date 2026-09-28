import { useMemo, useState } from 'react'

import { Field } from '../Field.jsx'
import { CURRENCIES } from '../../data/quotation.js'
import { formatMoney, previewTotals, toAmountInput } from '../../lib/money.js'

const BLANK_ITEM = { description: '', quantity: '1', unit_price: '' }

function blankDraft(lead) {
  return {
    currency: 'GBP',
    discount: '0',
    notes: '',
    // Seeded from the lead so the common case is one keystroke from complete.
    items: [
      {
        ...BLANK_ITEM,
        description: `${lead.service} — ${lead.location}`,
      },
    ],
  }
}

/**
 * Client-side validation mirroring the server's rules.
 *
 * This exists to avoid a pointless round trip and to show the problem next to
 * the field. The server re-validates everything; a disagreement is a server
 * bug, never a way around a rule.
 */
function validate(draft) {
  const errors = {}
  const filled = draft.items.filter(
    (item) => item.description.trim() !== '' || item.unit_price !== '',
  )

  if (filled.length === 0) {
    errors.items = 'Add at least one line item with a description and price.'
  }

  const { lines, subtotal } = previewTotals(draft.items, draft.discount)

  draft.items.forEach((item, index) => {
    const quantity = Number(item.quantity)
    const unitPrice = Number(item.unit_price)

    if (!item.description.trim() && item.unit_price !== '') {
      errors[`item-${index}`] = 'Enter a description for this line.'
    } else if (item.description.trim() && (!Number.isFinite(unitPrice) || unitPrice < 0)) {
      errors[`item-${index}`] = 'Unit price must be zero or more.'
    } else if (item.description.trim() && (!Number.isFinite(quantity) || quantity <= 0)) {
      errors[`item-${index}`] = 'Quantity must be greater than zero.'
    }
  })

  const discount = Number(draft.discount)
  if (!Number.isFinite(discount) || discount < 0) {
    errors.discount = 'Discount cannot be negative.'
  } else if (discount > subtotal) {
    errors.discount = `Discount cannot be greater than the subtotal (${formatMoney(
      subtotal,
      draft.currency,
    )}).`
  }

  // A total of zero is almost always a data-entry slip rather than a free job.
  if (!errors.items && !errors.discount && lines.length > 0 && subtotal === 0) {
    errors.items = 'The quotation total is zero. Check the quantities and prices.'
  }

  return errors
}

/**
 * The quotation editor.
 *
 * Line items are edited locally and the whole document is saved in one POST,
 * which keeps the save atomic: the server never sees a half-applied edit.
 * Displayed totals come from `previewTotals` for immediate feedback only — what
 * is persisted is always recalculated by the server.
 */
export function QuotationEditor({ lead, quotation, onSave, onCancel, saving, error }) {
  const [draft, setDraft] = useState(() =>
    quotation
      ? {
          currency: quotation.currency,
          discount: toAmountInput(quotation.discount),
          notes: quotation.notes ?? '',
          items: quotation.items.map((item) => ({
            description: item.description,
            quantity: toAmountInput(item.quantity),
            unit_price: toAmountInput(item.unit_price),
          })),
        }
      : blankDraft(lead),
  )

  const errors = useMemo(() => validate(draft), [draft])
  const hasErrors = Object.keys(errors).length > 0
  const { lines, subtotal, total } = previewTotals(draft.items, draft.discount)
  const isEditing = Boolean(quotation)

  function updateItem(index, key, value) {
    setDraft((current) => ({
      ...current,
      items: current.items.map((item, i) =>
        i === index ? { ...item, [key]: value } : item,
      ),
    }))
  }

  function addItem() {
    setDraft((current) => ({ ...current, items: [...current.items, { ...BLANK_ITEM }] }))
  }

  function removeItem(index) {
    setDraft((current) => ({
      ...current,
      items: current.items.filter((_, i) => i !== index),
    }))
  }

  return (
    <form
      className="crm-quote-editor"
      onSubmit={(event) => {
        event.preventDefault()
        if (hasErrors || saving) return
        onSave(draft)
      }}
    >
      <div className="crm-quote-editor__context">
        <div>
          <span className="crm-quote-editor__context-label">Customer</span>
          <span className="crm-quote-editor__context-value">
            {lead.customer_name}
          </span>
        </div>
        <div>
          <span className="crm-quote-editor__context-label">Service</span>
          <span className="crm-quote-editor__context-value">{lead.service}</span>
        </div>
        <div>
          <span className="crm-quote-editor__context-label">Location</span>
          <span className="crm-quote-editor__context-value">{lead.location}</span>
        </div>
      </div>

      <div className="crm-quote-items">
        <div className="crm-quote-items__head" aria-hidden="true">
          <span>Description</span>
          <span className="crm-quote-items__num">Qty</span>
          <span className="crm-quote-items__num">Unit price</span>
          <span className="crm-quote-items__num">Line total</span>
          <span className="crm-quote-items__remove" />
        </div>

        {draft.items.map((item, index) => (
          <div className="crm-quote-item" key={index}>
            <div className="field">
              <label className="sr-only" htmlFor={`crm-quote-desc-${index}`}>
                Description for line {index + 1}
              </label>
              <input
                id={`crm-quote-desc-${index}`}
                className="input"
                type="text"
                maxLength={500}
                value={item.description}
                placeholder="Deep clean — open-plan office"
                aria-invalid={errors[`item-${index}`] ? true : undefined}
                onChange={(event) =>
                  updateItem(index, 'description', event.target.value)
                }
              />
              {errors[`item-${index}`] ? (
                <p className="field__error">{errors[`item-${index}`]}</p>
              ) : null}
            </div>

            <div className="field">
              <label className="sr-only" htmlFor={`crm-quote-qty-${index}`}>
                Quantity for line {index + 1}
              </label>
              <input
                id={`crm-quote-qty-${index}`}
                className="input crm-quote-item__num"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={item.quantity}
                onChange={(event) => updateItem(index, 'quantity', event.target.value)}
              />
            </div>

            <div className="field">
              <label className="sr-only" htmlFor={`crm-quote-price-${index}`}>
                Unit price for line {index + 1}
              </label>
              <input
                id={`crm-quote-price-${index}`}
                className="input crm-quote-item__num"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={item.unit_price}
                placeholder="0.00"
                onChange={(event) =>
                  updateItem(index, 'unit_price', event.target.value)
                }
              />
            </div>

            <div className="crm-quote-item__total" aria-hidden="true">
              {formatMoney(lines[index]?.line_total ?? 0, draft.currency)}
            </div>

            <button
              type="button"
              className="crm-quote-item__remove"
              onClick={() => removeItem(index)}
              disabled={draft.items.length === 1}
              aria-label={`Remove line ${index + 1}`}
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
        ))}
      </div>

      <button type="button" className="crm-quote-add" onClick={addItem}>
        + Add line item
      </button>

      {errors.items ? (
        <p className="field__error" role="alert">
          {errors.items}
        </p>
      ) : null}

      <div className="crm-quote-totals">
        <div className="crm-quote-totals__controls">
          <Field id="crm-quote-currency" label="Currency">
            {({ id, describedBy }) => (
              <select
                id={id}
                className="select"
                value={draft.currency}
                aria-describedby={describedBy}
                disabled={saving}
                onChange={(event) =>
                  setDraft((c) => ({ ...c, currency: event.target.value }))
                }
              >
                {CURRENCIES.map((c) => (
                  <option value={c.code} key={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            )}
          </Field>

          <Field id="crm-quote-discount" label="Discount" error={errors.discount}>
            {({ id, describedBy, invalid }) => (
              <input
                id={id}
                className="input"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={draft.discount}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                disabled={saving}
                onChange={(event) =>
                  setDraft((c) => ({ ...c, discount: event.target.value }))
                }
              />
            )}
          </Field>
        </div>

        <dl className="crm-quote-summary">
          <div>
            <dt>Subtotal</dt>
            <dd>{formatMoney(subtotal, draft.currency)}</dd>
          </div>
          <div>
            <dt>Discount</dt>
            <dd>
              &minus;
              {formatMoney(
                Number(draft.discount) || 0,
                draft.currency,
              )}
            </dd>
          </div>
          <div className="crm-quote-summary__total">
            <dt>Total</dt>
            <dd>{formatMoney(total, draft.currency)}</dd>
          </div>
        </dl>
      </div>

      <Field
        id="crm-quote-notes"
        label="Notes and terms"
        optional
        hint="Shown to the customer on the quotation."
      >
        {({ id, describedBy }) => (
          <textarea
            id={id}
            className="textarea"
            rows={3}
            maxLength={4000}
            value={draft.notes}
            placeholder="Prices exclude VAT. Quotation valid for 30 days."
            aria-describedby={describedBy}
            disabled={saving}
            onChange={(event) =>
              setDraft((c) => ({ ...c, notes: event.target.value }))
            }
          />
        )}
      </Field>

      {error ? (
        <div className="crm-alert" role="alert">
          <p>{error}</p>
        </div>
      ) : null}

      <div className="crm-quote-editor__actions">
        <button
          type="submit"
          className="btn btn--primary"
          disabled={saving || hasErrors}
        >
          {saving ? 'Saving…' : isEditing ? 'Save draft' : 'Create draft'}
        </button>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={onCancel}
          disabled={saving}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
