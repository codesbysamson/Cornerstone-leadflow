import { useCallback, useEffect, useState } from 'react'

import {
  clearFollowUp,
  createNote,
  listLeads,
  listNotes,
  saveFollowUp,
  updateLeadStatus,
} from '../../lib/crmApi.js'
import { Dashboard } from './Dashboard.jsx'
import { LeadDetail } from './LeadDetail.jsx'
import { LeadList } from './LeadList.jsx'

/**
 * The staff lead CRM.
 *
 * All leads are held in one `leads` array and the detail view is a selection
 * into it. That keeps every mutation trivially consistent: the updated lead
 * from the server replaces its entry in place, and the dashboard counts and
 * follow-up buckets stay correct without a refetch.
 */
export function CrmApp({ onExit }) {
  const [leads, setLeads] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Notes are per-lead and fetched on demand, so they are kept outside the
  // leads array to keep list loads cheap.
  const [notes, setNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)

    try {
      const data = await listLeads()
      setLeads(Array.isArray(data) ? data : [])
    } catch (error) {
      setLoadError(error.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const selectedLead =
    selectedId === null
      ? null
      : (leads.find((lead) => lead.id === selectedId) ?? null)

  // Load this lead's history whenever the selection changes. The guard stops a
  // slow response for a previously selected lead from overwriting the current
  // one's notes.
  useEffect(() => {
    if (selectedLead === null) {
      setNotes([])
      return
    }

    let active = true
    setNotesLoading(true)

    listNotes(selectedLead.id)
      .then((data) => {
        if (active) setNotes(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (active) setNotes([])
      })
      .finally(() => {
        if (active) setNotesLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedLead?.id])

  /** Replaces a lead in place from the server's copy. */
  function applyLead(updated) {
    setLeads((current) =>
      current.map((lead) => (lead.id === updated.id ? updated : lead)),
    )
  }

  async function handleChangeStatus(status) {
    if (!selectedLead) return

    setSaving(true)
    setSaveError(null)

    try {
      applyLead(await updateLeadStatus(selectedLead.id, status))
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  /** Returns true when the note was confirmed persisted. */
  async function handleAddNote(body) {
    if (!selectedLead) return false

    setSaving(true)
    setSaveError(null)

    try {
      const created = await createNote(selectedLead.id, body)
      // Newest-first, matching the server's own ordering.
      setNotes((current) => [created, ...current])
      return true
    } catch (error) {
      setSaveError(error.message)
      return false
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveFollowUp(dueAt, action) {
    if (!selectedLead) return

    setSaving(true)
    setSaveError(null)

    try {
      applyLead(await saveFollowUp(selectedLead.id, dueAt, action))
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleClearFollowUp() {
    if (!selectedLead) return

    setSaving(true)
    setSaveError(null)

    try {
      applyLead(await clearFollowUp(selectedLead.id))
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  function handleSelect(leadId) {
    setSelectedId(leadId)
    setSaveError(null)
  }

  function handleBack() {
    setSelectedId(null)
    setSaveError(null)
    setNotes([])
  }

  return (
    <div className="crm">
      <header className="crm__appbar">
        <div className="container crm__appbar-inner">
          <div className="crm__identity">
            <span className="crm__mark" aria-hidden="true" />
            <span className="crm__identity-text">
              <span className="crm__product">Apex LeadFlow</span>
              <span className="crm__context">Internal · Lead management</span>
            </span>
          </div>

          <nav className="crm__nav" aria-label="CRM sections">
            <button
              type="button"
              className="crm__nav-item"
              aria-current={selectedLead ? undefined : 'page'}
              onClick={handleBack}
            >
              Leads
            </button>
            <button type="button" className="crm__exit" onClick={onExit}>
              Exit CRM
            </button>
          </nav>
        </div>
      </header>

      <main className="crm__main">
        {loading ? (
          <LoadingState />
        ) : loadError ? (
          <ErrorState message={loadError} onRetry={load} />
        ) : selectedLead ? (
          <LeadDetail
            lead={selectedLead}
            notes={notes}
            notesLoading={notesLoading}
            onBack={handleBack}
            onChangeStatus={handleChangeStatus}
            onAddNote={handleAddNote}
            onSaveFollowUp={handleSaveFollowUp}
            onClearFollowUp={handleClearFollowUp}
            saving={saving}
            error={saveError}
          />
        ) : leads.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <Dashboard leads={leads} onSelect={handleSelect} />
            <LeadList leads={leads} onSelect={handleSelect} />
          </>
        )}
      </main>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="crm-skeleton-group" role="status" aria-live="polite">
      <span className="sr-only">Loading leads…</span>
      <div className="crm-skeleton crm-skeleton--wide" aria-hidden="true" />
      <div className="crm-skeleton crm-skeleton--mid" aria-hidden="true" />
      <div className="crm-skeleton crm-skeleton--short" aria-hidden="true" />
    </div>
  )
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="crm-state" role="alert">
      <h2 className="crm-state__title">Leads could not be loaded</h2>
      <p className="crm-state__body">{message}</p>
      <div className="crm-state__actions">
        <button type="button" className="btn btn--primary" onClick={onRetry}>
          Try again
        </button>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="crm-state">
      <h2 className="crm-state__title">No leads yet</h2>
      <p className="crm-state__body">
        Enquiries submitted through the Apex website will appear here as soon as
        the first one arrives.
      </p>
    </div>
  )
}
