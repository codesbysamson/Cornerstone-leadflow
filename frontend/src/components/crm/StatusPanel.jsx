import { useEffect, useState } from 'react'

import { LEAD_STATUSES } from '../../data/statuses.js'
import { StatusBadge } from './StatusBadge.jsx'

/**
 * The status editor for a single lead.
 *
 * Isolated in its own component so an in-flight save re-renders only the
 * control, not the whole fact list.
 *
 * The local `draft` holds the pending choice so the displayed status keeps
 * showing the persisted value until the server confirms the change.
 */
export function StatusPanel({ lead, onChangeStatus, saving, error }) {
  const [draft, setDraft] = useState(lead.status)
  const isDirty = draft !== lead.status

  // Adopt a status changed from elsewhere (e.g. a reload of the same lead) so
  // the select never shows a stale value after a save.
  useEffect(() => {
    setDraft(lead.status)
  }, [lead.status])

  return (
    <div className="crm-panel crm-status">
      <div className="crm-status__current">
        <span className="crm-status__label">Current status</span>
        <StatusBadge status={lead.status} />
      </div>

      <form
        className="crm-status__form"
        onSubmit={(event) => {
          event.preventDefault()
          onChangeStatus(draft)
        }}
      >
        <div className="field">
          <label className="field__label" htmlFor="crm-status-select">
            Change status
          </label>
          <select
            id="crm-status-select"
            className="select"
            value={draft}
            disabled={saving}
            onChange={(event) => setDraft(event.target.value)}
          >
            {LEAD_STATUSES.map(({ value, label }) => (
              <option value={value} key={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="crm-status__actions">
          <button
            type="submit"
            className="btn btn--primary"
            /* Disabled until a different value is chosen, so an accidental
               double-click cannot fire a no-op request. */
            disabled={saving || !isDirty}
          >
            {saving ? 'Updating…' : 'Update status'}
          </button>
        </div>

        {error ? (
          <p className="field__error" role="alert">
            {error}
          </p>
        ) : (
          <p className="crm-status__hint">
            {isDirty
              ? 'Save to record this change.'
              : 'Select a different status to enable the update.'}
          </p>
        )}
      </form>
    </div>
  )
}
