import { LEAD_STATUSES } from '../../data/statuses.js'
import { formatDate } from '../../lib/format.js'

/**
 * Pipeline counts. Rendered as a bordered tile row rather than a chart: a
 * staff user needs exact numbers to work through the queue, and no
 * dependencies were added for this milestone.
 */
export function Dashboard({ leads }) {
  const counts = new Map()
  let open = 0

  for (const lead of leads) {
    counts.set(lead.status, (counts.get(lead.status) ?? 0) + 1)
    if (lead.status !== 'WON' && lead.status !== 'LOST') {
      open += 1
    }
  }

  const newest = leads[0]

  return (
    <>
      <div className="crm__page-head">
        <div>
          <h1 className="crm__page-title">Lead pipeline</h1>
          <p className="crm__page-meta">
            {leads.length} {leads.length === 1 ? 'enquiry' : 'enquiries'} captured
            from the website
            {newest ? ` · newest received ${formatDate(newest.created_at)}` : ''}
          </p>
        </div>
      </div>

      <div className="crm__stats">
        <div className="crm-stat crm-stat--total">
          <span className="crm-stat__label">Total</span>
          <span className="crm-stat__value">{leads.length}</span>
        </div>
        <div className="crm-stat">
          <span className="crm-stat__label">Open</span>
          <span className="crm-stat__value">{open}</span>
        </div>
        {LEAD_STATUSES.map(({ value, label }) => (
          <div className="crm-stat" key={value}>
            <span className="crm-stat__label">{label}</span>
            <span className="crm-stat__value">{counts.get(value) ?? 0}</span>
          </div>
        ))}
      </div>
    </>
  )
}
