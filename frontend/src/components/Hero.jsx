export function Hero({ onStartQuote }) {
  return (
    <section className="hero" id="top">
      <div className="container hero__inner">
        <div>
          <p className="eyebrow">Commercial cleaning &amp; facility support</p>
          <h1>Facility services that fit how your building actually runs.</h1>
          <p className="hero__lead">
            Apex plans, schedules and delivers cleaning and maintenance support
            for workplaces and managed properties — with the scope agreed in
            writing before any work is booked.
          </p>
          <div className="btn-row">
            <button
              className="btn btn--primary"
              type="button"
              onClick={onStartQuote}
            >
              Request a Quote
            </button>
            <a className="btn btn--secondary" href="#services">
              Explore Services
            </a>
          </div>
          <ul className="hero__meta">
            <li>Out-of-hours scheduling</li>
            <li>Recurring or one-off</li>
            <li>Structured quoting</li>
          </ul>
        </div>

        <aside className="hero__panel" aria-label="Service arrangements">
          <h2>Service arrangements</h2>
          <ul className="hero__panel-list">
            <li>
              <span className="hero__panel-key">Scope</span>
              <span>
                <strong>Agreed in writing.</strong> Areas, tasks and frequency
                are confirmed before scheduling.
              </span>
            </li>
            <li>
              <span className="hero__panel-key">Timing</span>
              <span>
                <strong>Built around your hours.</strong> Early, late and
                weekend working where access allows.
              </span>
            </li>
            <li>
              <span className="hero__panel-key">Records</span>
              <span>
                <strong>One channel.</strong> Requests, changes and additional
                scope are captured in a single place.
              </span>
            </li>
          </ul>
        </aside>
      </div>
    </section>
  )
}
