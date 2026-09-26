export function QuoteCta({ onStartQuote }) {
  return (
    <section className="section section--paper">
      <div className="container">
        <div className="closing">
          <div>
            <h2>Request a quote</h2>
            <p>
              Tell us the service, the property and the arrangements you need.
              The request is recorded as a structured enquiry so the scope is
              clear before anything is scheduled.
            </p>
          </div>
          <div className="closing__actions">
            <button
              className="btn btn--primary btn--block"
              type="button"
              onClick={onStartQuote}
            >
              Request a Quote
            </button>
            <p className="closing__note">
              Takes around two minutes. No obligation.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
