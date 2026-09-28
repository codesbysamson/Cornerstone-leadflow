import { ActivityList } from './ActivityList.jsx'
import { FollowUpPanel } from './FollowUpPanel.jsx'
import { QuotationList } from './QuotationList.jsx'
import { StatusPanel } from './StatusPanel.jsx'
import { formatDateTime, orDash } from '../../lib/format.js'
import { buildLeadWhatsAppUrl } from '../../lib/whatsapp.js'

/**
 * Enquiry facts, in the order a sales user reads them: who, what they need,
 * where, when, then the captured requirements.
 */
const FACTS = [
  { label: 'Customer', get: (lead) => lead.customer_name },
  { label: 'Email', get: (lead) => lead.email },
  { label: 'Phone', get: (lead) => lead.phone },
  { label: 'Service', get: (lead) => lead.service },
  { label: 'Property type', get: (lead) => lead.property_type },
  { label: 'Location', get: (lead) => lead.location },
  { label: 'Property size', get: (lead) => lead.property_size },
  { label: 'Frequency', get: (lead) => lead.frequency },
  { label: 'Preferred date', get: (lead) => lead.preferred_date },
  { label: 'Source', get: (lead) => lead.source },
  { label: 'Received', get: (lead) => formatDateTime(lead.created_at) },
]

export function LeadDetail({
  lead,
  notes,
  notesLoading,
  onBack,
  onChangeStatus,
  onAddNote,
  onSaveFollowUp,
  onClearFollowUp,
  quotations,
  quotationBusy,
  onCreateQuotation,
  onOpenQuotation,
  saving,
  error,
}) {
  const whatsappUrl = buildLeadWhatsAppUrl(lead)

  return (
    <>
      <button type="button" className="crm-back" onClick={onBack}>
        <span aria-hidden="true">&larr;</span> Back to all leads
      </button>

      <div className="crm-detail">
        <div className="crm-detail__main">
          <div className="crm-panel">
            <div className="crm-panel__head">
              <h2 className="crm-panel__title">
                Enquiry #{lead.id} &middot; {lead.customer_name}
              </h2>
              <WhatsAppAction url={whatsappUrl} phone={lead.phone} />
            </div>

            <dl className="crm-facts">
              {FACTS.map(({ label, get }) => {
                const value = get(lead)
                return (
                  <div className="crm-fact" key={label}>
                    <dt>{label}</dt>
                    <dd className={value ? undefined : 'is-empty'}>
                      {orDash(value)}
                    </dd>
                  </div>
                )
              })}

              <div className="crm-fact">
                <dt>Requirements</dt>
                <dd
                  className={
                    lead.requirements
                      ? 'crm-requirements'
                      : 'crm-requirements is-empty'
                  }
                >
                  {orDash(lead.requirements)}
                </dd>
              </div>
            </dl>
          </div>

          <ActivityList
            notes={notes}
            onAdd={onAddNote}
            saving={saving}
            error={error}
            loading={notesLoading}
          />

          <QuotationList
            quotations={quotations}
            onOpen={onOpenQuotation}
            onCreate={onCreateQuotation}
            busy={quotationBusy}
          />
        </div>

        <div className="crm-detail__side">
          <FollowUpPanel
            lead={lead}
            onSave={onSaveFollowUp}
            onClear={onClearFollowUp}
            saving={saving}
            error={error}
          />
          <StatusPanel
            lead={lead}
            onChangeStatus={onChangeStatus}
            saving={saving}
            error={error}
          />
        </div>
      </div>
    </>
  )
}

/**
 * Click-to-WhatsApp. Provider-free: a wa.me deep link that opens WhatsApp with
 * a prefilled message, which the staff member can edit before sending.
 *
 * `phone` is free text from the website and is never validated, so when it
 * cannot be normalised safely the number is shown as plain text and no link is
 * offered at all. A wrongly-routed link is worse than no link.
 */
function WhatsAppAction({ url, phone }) {
  if (!url) {
    return (
      <p className="crm-whatsapp crm-whatsapp--unavailable">
        <span className="crm-whatsapp__label">WhatsApp</span>
        <span className="crm-whatsapp__hint">
          Cannot build a WhatsApp link for &ldquo;{orDash(phone)}&rdquo;. Open
          WhatsApp and start the chat manually.
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
      <span className="crm-whatsapp__label">Message on WhatsApp</span>
      <span className="crm-whatsapp__hint">
        Opens WhatsApp with a prefilled message you can edit before sending.
      </span>
    </a>
  )
}
