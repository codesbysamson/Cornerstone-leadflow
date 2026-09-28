import { useEffect, useState } from 'react'

import { Field } from '../Field.jsx'
import { formatDateTime, orDash, toLocalInputValue, toUtcIso } from '../../lib/format.js'

/**
 * Set, reschedule or clear the single next follow-up for a lead.
 *
 * Mirrors StatusPanel: the displayed state always shows what is persisted, and
 * the local draft holds a pending choice until the server confirms it. Reschedule
 * pre-fills the control from the stored value, so changing a date is an edit
 * rather than a re-entry.
 */
export function FollowUpPanel({ lead, onSave, onClear, saving, error }) {
  const hasFollowUp = Boolean(lead.next_follow_up_at)
  const [dueAt, setDueAt] = useState('')
  const [action, setAction] = useState('')

  // Adopt the stored follow-up whenever it changes, including after a save or
  // a clear, so the control never shows a stale value.
  useEffect(() => {
    setDueAt(toLocalInputValue(lead.next_follow_up_at))
    setAction(lead.next_follow_up_action ?? '')
  }, [lead.next_follow_up_at, lead.next_follow_up_action])

  const isDirty = dueAt !== '' && action.trim() !== ''
  const sameAsStored =
    dueAt === toLocalInputValue(lead.next_follow_up_at) &&
    action === (lead.next_follow_up_action ?? '')

  return (
    <div className="crm-panel crm-status">
      <div className="crm-status__current">
        <span className="crm-status__label">Next follow-up</span>
      </div>

      {hasFollowUp ? (
        <dl className="crm-followup-current">
          <div>
            <dt>Due</dt>
            <dd>{formatDateTime(lead.next_follow_up_at)}</dd>
          </div>
          <div>
            <dt>Action</dt>
            <dd>{orDash(lead.next_follow_up_action)}</dd>
          </div>
        </dl>
      ) : (
        <p className="crm-status__hint crm-status__hint--block">
          No follow-up set for this lead.
        </p>
      )}

      <form
        className="crm-status__form"
        onSubmit={(event) => {
          event.preventDefault()
          const iso = toUtcIso(dueAt)
          if (iso) onSave(iso, action.trim())
        }}
      >
        <Field
          id="crm-follow-up-date"
          label={hasFollowUp ? 'Reschedule to' : 'Follow up on'}
          hint="Uses your device's local date and time."
        >
          {({ id, describedBy }) => (
            <input
              id={id}
              className="input"
              type="datetime-local"
              value={dueAt}
              aria-describedby={describedBy}
              disabled={saving}
              onChange={(event) => setDueAt(event.target.value)}
            />
          )}
        </Field>

        <Field
          id="crm-follow-up-action"
          label="Action or reason"
          hint="Short, e.g. Send revised quote"
        >
          {({ id, describedBy }) => (
            <input
              id={id}
              className="input"
              type="text"
              maxLength={255}
              placeholder="Send revised quote"
              value={action}
              aria-describedby={describedBy}
              disabled={saving}
              onChange={(event) => setAction(event.target.value)}
            />
          )}
        </Field>

        <div className="crm-status__actions">
          <button
            type="submit"
            className="btn btn--primary"
            /* Disabled until both fields are filled and something actually
               changed, so an accidental double-click cannot fire a no-op. */
            disabled={saving || !isDirty || sameAsStored}
          >
            {saving ? 'Saving…' : hasFollowUp ? 'Reschedule' : 'Set follow-up'}
          </button>

          {hasFollowUp ? (
            <button
              type="button"
              className="btn btn--secondary"
              disabled={saving}
              onClick={onClear}
            >
              Clear
            </button>
          ) : null}
        </div>

        {error ? (
          <p className="field__error" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  )
}
