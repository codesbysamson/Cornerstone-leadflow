import { formatDate, orDash } from '../../lib/format.js'
import { formatMoney } from '../../lib/money.js'
import { QuotationBadge } from './QuotationBadge.jsx'

/**
 * Every quotation raised against a lead, newest first.
 *
 * A lead can accumulate several quotations over its life, so this is a history
 * rather than a single value — which is why a lead with a rejected quote must
 * be able to raise a new one without losing the old.
 */
export function QuotationList({ quotations, onOpen, onCreate, busy }) {
  return (
    <div className="crm-panel crm-quotes">
      <div className="crm-panel__head">
        <h2 className="crm-panel__title">
          Quotations{quotations.length ? ` (${quotations.length})` : ''}
        </h2>
        <button
          type="button"
          className="btn btn--primary crm-quotes__create"
          onClick={onCreate}
          disabled={busy}
        >
          Create quotation
        </button>
      </div>

      {quotations.length === 0 ? (
        <p className="crm-quotes__empty">
          No quotations yet. Create one to price this enquiry and send it to the
          customer.
        </p>
      ) : (
        <ul className="crm-quotes__list">
          {quotations.map((quotation) => (
            <li className="crm-quotes__item" key={quotation.id}>
              <button
                type="button"
                className="crm-quotes__open"
                onClick={() => onOpen(quotation.id)}
                disabled={busy}
              >
                <span className="crm-quotes__ref">{quotation.reference}</span>
                <span className="crm-quotes__items">
                  {quotation.items.length}{' '}
                  {quotation.items.length === 1 ? 'item' : 'items'} &middot;{' '}
                  {orDash(quotation.notes)?.slice(0, 60) || 'No terms'}
                </span>
                <span className="crm-quotes__total">
                  {formatMoney(quotation.total, quotation.currency)}
                </span>
                <QuotationBadge status={quotation.status} />
                <span className="crm-quotes__date">
                  {formatDate(quotation.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
