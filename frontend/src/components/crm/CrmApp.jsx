import { useCallback, useEffect, useState } from 'react'

import {
  clearFollowUp,
  createNote,
  listLeads,
  listNotes,
  saveFollowUp,
  updateLeadStatus,
} from '../../lib/crmApi.js'
import {
  createQuotation,
  getQuotation,
  listQuotations,
  transitionQuotation,
  updateQuotation,
} from '../../lib/quotationApi.js'
import { Dashboard } from './Dashboard.jsx'
import { LeadDetail } from './LeadDetail.jsx'
import { LeadList } from './LeadList.jsx'
import { QuotationEditor } from './QuotationEditor.jsx'
import { QuotationPreview } from './QuotationPreview.jsx'

/**
 * The staff lead CRM.
 *
 * All leads are held in one `leads` array and the detail view is a selection
 * into it. That keeps every mutation trivially consistent: the updated lead
 * from the server replaces its entry in place, and the dashboard counts and
 * follow-up buckets stay correct without a refetch.
 *
 * Quotations add a third level of nesting — lead, then quotation — held in
 * `quotationView` so the quotation sub-screen is a mode rather than a route.
 * The back stack is tracked explicitly because a quotation opened from a
 * quotation (a second version of the same quote) must still return sensibly.
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

  // 'list' | 'editor' | 'preview', plus which quotation is in play.
  const [quotationView, setQuotationView] = useState('list')
  const [editingQuotation, setEditingQuotation] = useState(null)
  const [quotation, setQuotation] = useState(null)
  const [quotations, setQuotations] = useState([])
  const [quotationError, setQuotationError] = useState(null)

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

  // -------------------------------------------------------------------------
  // Quotations
  // -------------------------------------------------------------------------

  // Reload the lead's quotations whenever the lead selection changes.
  useEffect(() => {
    if (selectedId === null) {
      setQuotations([])
      return
    }

    let active = true
    listQuotations(selectedId)
      .then((data) => {
        if (active) setQuotations(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (active) setQuotations([])
      })

    return () => {
      active = false
    }
  }, [selectedId])

  function openQuotationEditor(existing = null) {
    setEditingQuotation(existing)
    setQuotationError(null)
    setQuotationView('editor')
  }

  function openQuotationPreview(id) {
    setQuotationError(null)
    setQuotationView('preview')
    // The full document is fetched on open rather than trusted from the list
    // summary, so the preview is never a partial record.
    getQuotationSafely(id)
  }

  async function getQuotationSafely(id) {
    try {
      const data = await getQuotation(id)
      setQuotation(data)
    } catch (error) {
      setQuotationError(error.message)
    }
  }

  /** Replaces a quotation in the history list, newest first. */
  function applyQuotation(updated) {
    setQuotation(updated)
    setQuotations((current) => {
      const without = current.filter((q) => q.id !== updated.id)
      return [updated, ...without].sort((a, b) => b.id - a.id)
    })
  }

  async function handleSaveQuotation(draft) {
    if (!selectedLead) return

    setSaving(true)
    setQuotationError(null)

    try {
      const saved = editingQuotation
        ? await updateQuotation(editingQuotation.id, draft)
        : await createQuotation(selectedLead.id, draft)

      applyQuotation(saved)
      setEditingQuotation(null)
      setQuotationView('preview')
    } catch (error) {
      // The editor stays open with its contents intact so nothing is retyped.
      setQuotationError(error.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleTransitionQuotation(status) {
    if (!quotation) return

    setSaving(true)
    setQuotationError(null)

    try {
      const updated = await transitionQuotation(quotation.id, status)
      applyQuotation(updated)

      // Sending a quotation moves the lead to QUOTE_SENT on the server, so the
      // lead row held locally is refreshed from the server rather than patched.
      const refreshed = leads.find((lead) => lead.id === updated.lead_id)
      if (refreshed) {
        const data = await listLeads()
        if (Array.isArray(data)) setLeads(data)
      }
    } catch (error) {
      setQuotationError(error.message)
    } finally {
      setSaving(false)
    }
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
    setQuotationError(null)
    // Reset the quotation sub-screen so opening another lead never shows the
    // previous lead's quotation.
    setQuotationView('list')
    setQuotation(null)
    setEditingQuotation(null)
  }

  function handleBack() {
    setSelectedId(null)
    setSaveError(null)
    setNotes([])
    setQuotationView('list')
    setQuotation(null)
    setEditingQuotation(null)
  }

  /** Returns from a quotation sub-screen to the lead it belongs to. */
  function handleBackFromQuotation() {
    setQuotationView('list')
    setQuotation(null)
    setEditingQuotation(null)
    setQuotationError(null)
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
          renderLeadArea()
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

  /**
   * The lead detail, or one of the two quotation sub-screens.
   *
   * Extracted so the nested quotation views read clearly instead of burying the
   * main render in conditionals.
   */
  function renderLeadArea() {
    if (quotationView === 'editor') {
      return (
        <QuotationEditor
          lead={selectedLead}
          quotation={editingQuotation}
          onSave={handleSaveQuotation}
          onCancel={handleBackFromQuotation}
          saving={saving}
          error={quotationError}
        />
      )
    }

    if (quotationView === 'preview' && quotation) {
      return (
        <>
          <button
            type="button"
            className="crm-back"
            onClick={handleBackFromQuotation}
          >
            <span aria-hidden="true">&larr;</span> Back to {selectedLead.customer_name}
          </button>
          <QuotationPreview
            lead={selectedLead}
            quotation={quotation}
            onEdit={() => openQuotationEditor(quotation)}
            onTransition={handleTransitionQuotation}
            busy={saving}
          />
          {quotationError ? (
            <div className="crm-alert" role="alert">
              <p>{quotationError}</p>
            </div>
          ) : null}
        </>
      )
    }

    return (
      <LeadDetail
        lead={selectedLead}
        notes={notes}
        notesLoading={notesLoading}
        onBack={handleBack}
        onChangeStatus={handleChangeStatus}
        onAddNote={handleAddNote}
        onSaveFollowUp={handleSaveFollowUp}
        onClearFollowUp={handleClearFollowUp}
        onSaveQuotation={handleSaveQuotation}
        saving={saving}
        error={saveError}
        quotations={quotations}
        quotationBusy={saving}
        onCreateQuotation={() => openQuotationEditor(null)}
        onOpenQuotation={openQuotationPreview}
      />
    )
  }
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
