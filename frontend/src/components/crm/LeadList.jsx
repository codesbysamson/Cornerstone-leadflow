import { bucketFollowUps } from '../../lib/followUp.js'
import { formatDate, formatDateTime, orDash } from '../../lib/format.js'
import { StatusBadge } from './StatusBadge.jsx'

/**
 * The lead queue, newest first.
 *
 * Each row is operable as a whole (click) and exposes a real button for the
 * customer name, so keyboard and screen-reader users get a single predictable
 * control rather than a div with a click handler.
 */
export function LeadList({ leads, onSelect }) {
  // One shared clock for the whole render, so an overdue row cannot disagree
  // with the Overdue count above it.
  const now = new Date()
  const overdueIds = new Set(bucketFollowUps(leads, now).overdue.map((l) => l.id))

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
            Website enquiries, newest first. Select a lead to view full details,
            its activity history, and to change its status or follow-up.
          </caption>
          <thead>
            <tr>
              <th scope="col">Ref</th>
              <th scope="col">Customer</th>
              <th scope="col">Service</th>
              <th scope="col">Location</th>
              <th scope="col">Status</th>
              <th scope="col">Next follow-up</th>
              <th scope="col">Received</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => {
              const isOverdue = overdueIds.has(lead.id)
              return (
                <tr
                  key={lead.id}
                  onClick={() => onSelect(lead.id)}
                  className={isOverdue ? 'is-overdue' : undefined}
                >
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
                  <td className="crm-table__date">
                    {lead.next_follow_up_at ? (
                      <>
                        <span className={isOverdue ? 'crm-followup-overdue' : undefined}>
                          {isOverdue ? 'Overdue · ' : ''}
                          {formatDateTime(lead.next_follow_up_at)}
                        </span>
                        <span className="crm-table__sub">
                          {orDash(lead.next_follow_up_action)}
                        </span>
                      </>
                    ) : (
                      <span className="crm-table__sub">Not set</span>
                    )}
                  </td>
                  <td className="crm-table__date">{formatDate(lead.created_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
