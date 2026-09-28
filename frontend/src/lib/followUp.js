/**
 * Follow-up bucketing for the CRM dashboard.
 *
 * Deliberately computed on the client from a single `now`, using the viewing
 * staff member's own clock. "Due today" is a statement about the working day
 * of the person looking at the dashboard, not about UTC — if the API bucketed
 * it, an operator outside UTC would see tomorrow's work counted as today's.
 * It also means no server-side timezone configuration to get wrong.
 */

/** Closed leads are not chased, so they never count as due or overdue. */
const CLOSED_STATUSES = new Set(['WON', 'LOST'])

function parse(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** True when two instants fall on the same local calendar day. */
function isSameLocalDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

/**
 * Splits leads into overdue and due-today buckets.
 *
 * The two are mutually exclusive: a follow-up earlier today that has already
 * passed is overdue, not "due today". The past is therefore accounted for
 * exactly once and nothing is double counted.
 *
 * `now` is passed in rather than read from the clock here so that a single
 * render pass cannot classify the same lead into two buckets if the minute
 * rolls over mid-render.
 */
export function bucketFollowUps(leads, now = new Date()) {
  const overdue = []
  const dueToday = []

  for (const lead of leads) {
    if (CLOSED_STATUSES.has(lead.status)) continue

    const dueAt = parse(lead.next_follow_up_at)
    if (!dueAt) continue

    if (dueAt.getTime() < now.getTime()) {
      overdue.push(lead)
    } else if (isSameLocalDay(dueAt, now)) {
      dueToday.push(lead)
    }
  }

  // Soonest first: the next call the user owes is at the top.
  const bySoonest = (a, b) =>
    parse(a.next_follow_up_at) - parse(b.next_follow_up_at)

  overdue.sort(bySoonest)
  dueToday.sort(bySoonest)

  return { overdue, dueToday }
}
