import { useCallback, useEffect, useState } from 'react'

import { listLeads, updateLeadStatus } from '../../lib/crmApi.js'
import { Dashboard } from './Dashboard.jsx'
import { LeadDetail } from './LeadDetail.jsx'
import { LeadList } from './LeadList.jsx'

/**
 * The staff lead CRM.
 *
 * All leads are held in one `leads` array and the detail view is a selection
 * into it. That keeps a status change trivially consistent: the updated lead
 * from the server replaces its entry in place, and the dashboard counts stay
 * correct without a refetch.
 */
export function CrmApp({ onExit }) {
  const [leads, setLeads] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

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

  async function handleChangeStatus(status) {
    if (!selectedLead) return

    setSaving(true)
    setSaveError(null)

    try {
      // Trust the server's copy of the lead, so the displayed status always
      // reflects what was actually persisted.
      const updated = await updateLeadStatus(selectedLead.id, status)
      setLeads((current) =>
        current.map((lead) => (lead.id === updated.id ? updated : lead)),
      )
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  function handleBack() {
    setSelectedId(null)
    setSaveError(null)
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
            onBack={handleBack}
            onChangeStatus={handleChangeStatus}
            saving={saving}
            error={saveError}
          />
        ) : leads.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <Dashboard leads={leads} />
            <LeadList leads={leads} onSelect={setSelectedId} />
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
