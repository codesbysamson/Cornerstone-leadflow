import { isEditable, nextStatuses } from '../../data/quotation.js'
import { formatMoney } from '../../lib/money.js'
import { formatDate, formatDateTime, orDash } from '../../lib/format.js'
import { buildWhatsAppUrl, quotationWhatsappMessage } from '../../lib/whatsapp.js'
import { QuotationBadge } from './QuotationBadge.jsx'

/**
 * The customer-facing quotation document, plus the staff actions around it.
 *
 * This is the screen a sales demonstration actually shows, so it reads as a
 * document rather than a form: identity block, itemised table, totals, terms.
 */
export function QuotationPreview({ lead, quotation, onEdit, onTransition, busy }) {
  const editable = isEditable(quotation.status)
  const available = nextStatuses(quotation.status)

  // Only the customer's own message goes into the link. Internal staff notes
  // must never leave the CRM via a prefilled message.
  const shareUrl = buildWhatsAppUrl(
    lead,
    quotationWhatsappMessage(lead, quotation, formatMoney),
  )

  return (
    <article className="crm-quote-doc">
      <header className="crm-quote-doc__head">
        <div className="crm-quote-doc__brand">
          <span className="crm-quote-doc__mark" aria-hidden="true" />
          <div>
            <p className="crm-quote-doc__company">Apex Facility Services</p>
            <p className="crm-quote-doc__tagline">
              Commercial cleaning &amp; facilities maintenance
            </p>
          </div>
        </div>

        <div className="crm-quote-doc__ref">
          <p className="crm-quote-doc__ref-label">Quotation</p>
          <p className="crm-quote-doc__ref-value">{quotation.reference}</p>
          <QuotationBadge status={quotation.status} />
        </div>
      </header>

      <div className="crm-quote-doc__parties">
        <div>
          <h3 className="crm-quote-doc__section">Prepared for</h3>
          <p className="crm-quote-doc__party-name">{lead.customer_name}</p>
          <p className="crm-quote-doc__party-line">{orDash(lead.email)}</p>
          <p className="crm-quote-doc__party-line">{orDash(lead.phone)}</p>
          <p className="crm-quote-doc__party-line">{orDash(lead.location)}</p>
        </div>

        <div>
          <h3 className="crm-quote-doc__section">Enquiry</h3>
          <dl className="crm-quote-doc__meta">
            <div>
              <dt>Service</dt>
              <dd>{orDash(lead.service)}</dd>
            </div>
            <div>
              <dt>Property</dt>
              <dd>{orDash(lead.property_type)}</dd>
            </div>
            {lead.property_size ? (
              <div>
                <dt>Size</dt>
                <dd>{lead.property_size}</dd>
              </div>
            ) : null}
            {lead.frequency ? (
              <div>
                <dt>Frequency</dt>
                <dd>{lead.frequency}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      </div>

      <div className="crm-quote-doc__table-wrap">
        <table className="crm-quote-doc__table">
          <caption className="sr-only">
            Quoted items for {lead.customer_name}
          </caption>
          <thead>
            <tr>
              <th scope="col">Description</th>
              <th scope="col" className="crm-quote-doc__num">Qty</th>
              <th scope="col" className="crm-quote-doc__num">Unit price</th>
              <th scope="col" className="crm-quote-doc__num">Line total</th>
            </tr>
          </thead>
          <tbody>
            {quotation.items.map((item) => (
              <tr key={item.id}>
                <td>{item.description}</td>
                <td className="crm-quote-doc__num">{formatQty(item.quantity)}</td>
                <td className="crm-quote-doc__num">
                  {formatMoney(item.unit_price, quotation.currency)}
                </td>
                <td className="crm-quote-doc__num">
                  {formatMoney(item.line_total, quotation.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="crm-quote-doc__foot">
        <dl className="crm-quote-doc__totals">
          <div>
            <dt>Subtotal</dt>
            <dd>{formatMoney(quotation.subtotal, quotation.currency)}</dd>
          </div>
          <div>
            <dt>Discount</dt>
            <dd>
              &minus;{formatMoney(quotation.discount, quotation.currency)}
            </dd>
          </div>
          <div className="crm-quote-doc__grand">
            <dt>Total ({quotation.currency})</dt>
            <dd>{formatMoney(quotation.total, quotation.currency)}</dd>
          </div>
        </dl>

        {quotation.notes ? (
          <div className="crm-quote-doc__terms">
            <h3 className="crm-quote-doc__section">Notes and terms</h3>
            <p className="crm-quote-doc__terms-body">{quotation.notes}</p>
          </div>
        ) : null}
      </div>

      <footer className="crm-quote-doc__meta-foot">
        <span>Created {formatDate(quotation.created_at)}</span>
        {quotation.updated_at &&
        quotation.updated_at !== quotation.created_at ? (
          <span>Last updated {formatDate(quotation.updated_at)}</span>
        ) : null}
        {quotation.sent_at ? (
          <span>Sent {formatDateTime(quotation.sent_at)}</span>
        ) : null}
      </footer>

      <div className="crm-quote-doc__actions">
        {editable ? (
          <button
            type="button"
            className="btn btn--primary"
            onClick={onEdit}
            disabled={busy}
          >
            Edit draft
          </button>
        ) : null}

        {available.map((status) => (
          <button
            key={status}
            type="button"
            className={`btn ${
              status === 'SENT' ? 'btn--primary' : 'btn--secondary'
            }`}
            onClick={() => onTransition(status)}
            disabled={busy}
          >
            Mark {status.charAt(0) + status.slice(1).toLowerCase()}
          </button>
        ))}

        <WhatsAppShare url={shareUrl} lead={lead} />
      </div>
    </article>
  )
}

function WhatsAppShare({ url, lead }) {
  if (!url) {
    return (
      <p className="crm-whatsapp crm-whatsapp--unavailable">
        <span className="crm-whatsapp__label">Share on WhatsApp</span>
        <span className="crm-whatsapp__hint">
          No link can be built for &ldquo;{orDash(lead.phone)}&rdquo;. Send the
          quotation by another method.
        </span>
      </p>
    )
  }

  return (
    <a
      className="crm-whatsapp"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
    >
      <span className="crm-whatsapp__label">Share on WhatsApp</span>
      <span className="crm-whatsapp__hint">
        Opens WhatsApp with a prefilled message. Nothing is sent automatically.
      </span>
    </a>
  )
}

/** Drops a trailing ".00" so 2.00 reads as 2 but 2.50 keeps its half. */
function formatQty(quantity) {
  const text = String(quantity)
  return text.endsWith('.00') ? text.slice(0, -3) : text
}
