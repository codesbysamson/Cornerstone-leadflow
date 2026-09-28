import { LEAD_STATUSES } from '../../data/statuses.js'
import { bucketFollowUps } from '../../lib/followUp.js'
import { formatDate } from '../../lib/format.js'

/**
 * Pipeline counts plus follow-up visibility.
 *
 * Rendered as a bordered tile row rather than a chart: a staff user needs
 * exact numbers to work through the queue, and no dependencies were added for
 * this milestone.
 *
 * `now` is resolved once here and passed down, so a render that spans a minute
 * boundary cannot classify one lead into both the Overdue and Due Today
 * buckets.
 */
export function Dashboard({ leads, onSelect }) {
  const now = new Date()
  const counts = new Map()
  let open = 0

  for (const lead of leads) {
    counts.set(lead.status, (counts.get(lead.status) ?? 0) + 1)
    if (lead.status !== 'WON' && lead.status !== 'LOST') {
      open += 1
    }
  }

  const { overdue, dueToday } = bucketFollowUps(leads, now)
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

      <FollowUpQueue
        title="Overdue"
        leads={overdue}
        now={now}
        tone="overdue"
        onSelect={onSelect}
      />
      <FollowUpQueue
        title="Due today"
        leads={dueToday}
        now={now}
        tone="today"
        onSelect={onSelect}
      />
    </>
  )
}

function FollowUpQueue({ title, leads, now, tone, onSelect }) {
  const empty =
    tone === 'overdue'
      ? 'Nothing is overdue. All follow-ups are still ahead of you.'
      : 'No follow-ups are due today.'

  return (
    <section className="crm-queue" aria-labelledby={`crm-queue-${tone}`}>
      <div className="crm-queue__head">
        <h2 className="crm-queue__title" id={`crm-queue-${tone}`}>
          {title}
          <span className="crm-queue__count">{leads.length}</span>
        </h2>
      </div>

      {leads.length === 0 ? (
        <p className="crm-queue__empty">{empty}</p>
      ) : (
        <ul className="crm-queue__list">
          {leads.map((lead) => (
            <li className="crm-queue__item" key={lead.id}>
              <button
                type="button"
                className="crm-queue__link"
                onClick={() => onSelect(lead.id)}
              >
                {lead.customer_name}
              </button>
              <span className="crm-queue__action">
                {lead.next_follow_up_action ?? 'Follow up'}
              </span>
              <span className="crm-queue__when">
                <time dateTime={lead.next_follow_up_at}>
                  {formatQueueTime(lead.next_follow_up_at, now, tone)}
                </time>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/**
 * Overdue reads as a date ("3 days late"), due today as a clock time. The
 * count of days is what a staff member actually acts on, and it is stated in
 * words so the signal is never carried by colour alone.
 */
function formatQueueTime(value, now, tone) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  if (tone === 'today') {
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const days = Math.floor((now.getTime() - date.getTime()) / 86_400_000)
  if (days < 1) {
    return 'Overdue — earlier today'
  }
  if (days === 1) return 'Overdue — 1 day late'
  return `Overdue — ${days} days late`
}
