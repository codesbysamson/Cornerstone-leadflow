export function QuoteSuccess({ lead, formData, onReturnHome, onStartAnother }) {
  const firstName = (lead.customer_name || formData.customer_name || '')
    .trim()
    .split(/\s+/)[0]

  const facts = [
    { term: 'Reference', value: lead.id, emphasis: true },
    { term: 'Service', value: lead.service },
    { term: 'Location', value: lead.location },
  ]

  return (
    <section className="success" aria-labelledby="success-heading">
      <p className="success__badge">Request received</p>

      <h1 id="success-heading">
        Thank you{firstName ? `, ${firstName}` : ''}.
      </h1>
      <p className="success__lead">
        Your quote request has been received. Our team will review the
        requirements you provided and follow up about your quotation.
      </p>

      <dl className="success__reference">
        {facts.map((fact) => (
          <div key={fact.term} className="success__fact">
            <dt>{fact.term}</dt>
            <dd className={fact.emphasis ? 'success__fact-value--ref' : undefined}>
              {fact.value}
            </dd>
          </div>
        ))}
      </dl>

      <ul className="success__what-next">
        <li>
          We have recorded your service, property details and requirements as
          a structured enquiry.
        </li>
        <li>That enquiry is reviewed against the scope of the work.</li>
        <li>
          We contact you on {lead.email} or {lead.phone} to discuss the
          quotation.
        </li>
      </ul>

      <p className="success__note">
        Keep the reference {lead.id} for your records. Quote turnaround depends
        on the size and detail of the site.
      </p>

      <div className="success__actions">
        <button className="btn btn--primary" type="button" onClick={onReturnHome}>
          Back to homepage
        </button>
        <button className="btn btn--secondary" type="button" onClick={onStartAnother}>
          Submit another request
        </button>
      </div>
    </section>
  )
}
