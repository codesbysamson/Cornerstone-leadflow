import { StatusPanel } from './StatusPanel.jsx'
import { formatDateTime, orDash } from '../../lib/format.js'

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

export function LeadDetail({ lead, onBack, onChangeStatus, saving, error }) {
  return (
    <>
      <button type="button" className="crm-back" onClick={onBack}>
        <span aria-hidden="true">&larr;</span> Back to all leads
      </button>

      <div className="crm-detail">
        <div className="crm-panel">
          <div className="crm-panel__head">
            <h2 className="crm-panel__title">
              Enquiry #{lead.id} &middot; {lead.customer_name}
            </h2>
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

        <StatusPanel
          lead={lead}
          onChangeStatus={onChangeStatus}
          saving={saving}
          error={error}
        />
      </div>
    </>
  )
}
