import { statusMeta } from '../../data/statuses.js'

/**
 * Renders a pipeline status. An unrecognised value still renders (as its raw
 * text) so an unexpected database value is visible rather than silently blank.
 */
export function StatusBadge({ status }) {
  const { label, tone } = statusMeta(status)

  return <span className={`crm-badge crm-badge--${tone}`}>{label}</span>
}
