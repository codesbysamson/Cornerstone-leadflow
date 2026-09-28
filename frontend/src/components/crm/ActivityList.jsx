import { useState } from 'react'

import { Field } from '../Field.jsx'
import { formatDateTime } from '../../lib/format.js'

const MAX_NOTE_LENGTH = 2000

/**
 * The activity history for a lead, plus the composer that adds to it.
 *
 * Notes are append-only, so there is no edit or delete control by design. The
 * server decides ordering; the list is rendered exactly as returned, which is
 * newest-first.
 */
export function ActivityList({ notes, onAdd, saving, error, loading }) {
  const [draft, setDraft] = useState('')
  const trimmed = draft.trim()
  const canSubmit = trimmed !== '' && trimmed.length <= MAX_NOTE_LENGTH

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit || saving) return

    // `onAdd` resolves true only once the note is confirmed persisted. The
    // draft is kept on failure so a dropped connection does not destroy
    // something the user just typed.
    const saved = await onAdd(trimmed)
    if (saved) setDraft('')
  }

  return (
    <div className="crm-panel crm-activity">
      <div className="crm-panel__head">
        <h2 className="crm-panel__title">
          Activity{notes.length ? ` (${notes.length})` : ''}
        </h2>
      </div>

      <form className="crm-activity__composer" onSubmit={handleSubmit}>
        <Field id="crm-note-body" label="Add a note">
          {({ id, describedBy }) => (
            <textarea
              id={id}
              className="textarea crm-activity__input"
              rows={3}
              maxLength={MAX_NOTE_LENGTH}
              placeholder="Called and left a voicemail. Wants a quote for the second floor."
              value={draft}
              aria-describedby={describedBy}
              disabled={saving}
              onChange={(event) => setDraft(event.target.value)}
            />
          )}
        </Field>

        <div className="crm-activity__actions">
          <span className="crm-activity__count">
            {trimmed.length}/{MAX_NOTE_LENGTH}
          </span>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={saving || !canSubmit}
          >
            {saving ? 'Saving…' : 'Add note'}
          </button>
        </div>

        {error ? (
          <p className="field__error" role="alert">
            {error}
          </p>
        ) : null}
      </form>

      {loading ? (
        <p className="crm-activity__empty" role="status">
          Loading activity&hellip;
        </p>
      ) : notes.length === 0 ? (
        <p className="crm-activity__empty">
          No activity yet. Notes you add here are kept with this lead.
        </p>
      ) : (
        <ol className="crm-activity__list">
          {notes.map((note) => (
            <li className="crm-activity__item" key={note.id}>
              <p className="crm-activity__body">{note.body}</p>
              <time className="crm-activity__time" dateTime={note.created_at}>
                {formatDateTime(note.created_at)}
              </time>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
