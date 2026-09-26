import { useCallback, useEffect, useState } from 'react'

import './styles/base.css'
import './styles/site.css'
import './styles/quote.css'
import './styles/crm.css'

import { Header } from './components/Header.jsx'
import { Hero } from './components/Hero.jsx'
import { Services } from './components/Services.jsx'
import { HowItWorks } from './components/HowItWorks.jsx'
import { WhyApex } from './components/WhyApex.jsx'
import { QuoteCta } from './components/QuoteCta.jsx'
import { Footer } from './components/Footer.jsx'
import { QuoteFlow } from './components/QuoteFlow.jsx'
import { CrmApp } from './components/crm/CrmApp.jsx'

/**
 * The CRM is reachable only by deep link (?view=crm) so staff can bookmark it
 * without it appearing in the public site navigation or footer.
 */
function initialView() {
  const requested = new URLSearchParams(window.location.search).get('view')
  return requested === 'crm' ? 'crm' : 'site'
}

export default function App() {
  const [view, setView] = useState(initialView)

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [view])

  const openQuote = useCallback(() => setView('quote'), [])

  // Drop the query param on exit so a refresh lands on the marketing site
  // instead of bouncing straight back into the CRM.
  const exitCrm = useCallback(() => {
    const url = new URL(window.location.href)
    url.searchParams.delete('view')
    window.history.replaceState(null, '', url)
    setView('site')
  }, [])

  if (view === 'crm') {
    return <CrmApp onExit={exitCrm} />
  }

  if (view === 'quote') {
    return (
      <div className="quote-page">
        <div className="quote-page__bar">
          <div className="container quote-page__bar-inner">
            <span className="brand">
              <span className="brand__mark" aria-hidden="true" />
              <span className="brand__text">
                <span className="brand__name">Apex Facility Services</span>
              </span>
            </span>
            <button className="quote-page__back" type="button" onClick={() => setView('site')}>
              <span aria-hidden="true">&larr;</span> Back to site
            </button>
          </div>
        </div>

        <main className="quote-page__main">
          <div className="container">
            <div className="quote-page__head">
              <h1>Request a quote</h1>
              <p>
                Five short steps. Your answers become a structured enquiry we
                can review and quote against.
              </p>
            </div>
            <QuoteFlow onExit={() => setView('site')} />
          </div>
        </main>
      </div>
    )
  }

  return (
    <>
      <Header onStartQuote={openQuote} />
      <main>
        <Hero onStartQuote={openQuote} />
        <Services />
        <HowItWorks />
        <WhyApex />
        <QuoteCta onStartQuote={openQuote} />
      </main>
      <Footer onStartQuote={openQuote} />
    </>
  )
}
