import { formatDate } from '../../lib/format.js'
import { StatusBadge } from './StatusBadge.jsx'

/**
 * The lead queue, newest first.
 *
 * Each row is operable as a whole (click) and exposes a real button for the
 * customer name, so keyboard and screen-reader users get a single predictable
 * control rather than a div with a click handler.
 */
export function LeadList({ leads, onSelect }) {
  return (
    <div className="crm-panel">
      <div className="crm-panel__head">
        <h2 className="crm-panel__title">Enquiries</h2>
        <span className="crm__page-meta">
          {leads.length} {leads.length === 1 ? 'record' : 'records'}
        </span>
      </div>

      <div className="crm-table-scroll">
        <table className="crm-table">
          <caption className="sr-only">
            Website enquiries, newest first. Select a lead to view full details
            and change its status.
          </caption>
          <thead>
            <tr>
              <th scope="col">Ref</th>
              <th scope="col">Customer</th>
              <th scope="col">Service</th>
              <th scope="col">Location</th>
              <th scope="col">Status</th>
              <th scope="col">Received</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} onClick={() => onSelect(lead.id)}>
                <td className="crm-table__ref">#{lead.id}</td>
                <td>
                  {/* stopPropagation keeps the row click from firing twice. */}
                  <button
                    type="button"
                    className="crm-table__link"
                    onClick={(event) => {
                      event.stopPropagation()
                      onSelect(lead.id)
                    }}
                  >
                    {lead.customer_name}
                  </button>
                </td>
                <td>{lead.service}</td>
                <td>{lead.location}</td>
                <td>
                  <StatusBadge status={lead.status} />
                </td>
                <td className="crm-table__date">{formatDate(lead.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
