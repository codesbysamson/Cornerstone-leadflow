const GROUPS = [
  {
    step: 1,
    title: 'Service',
    rows: [{ label: 'Service', field: 'service' }],
  },
  {
    step: 2,
    title: 'Property',
    rows: [
      { label: 'Property type', field: 'property_type' },
      { label: 'Location', field: 'location' },
      { label: 'Approximate size', field: 'property_size' },
      { label: 'Frequency', field: 'frequency' },
      { label: 'Preferred start date', field: 'preferred_date' },
    ],
  },
  {
    step: 3,
    title: 'Requirements',
    rows: [{ label: 'Requirements', field: 'requirements' }],
  },
  {
    step: 4,
    title: 'Contact',
    rows: [
      { label: 'Full name', field: 'customer_name' },
      { label: 'Email address', field: 'email' },
      { label: 'Phone number', field: 'phone' },
    ],
  },
]

function formatValue(field, value) {
  if (field !== 'preferred_date' || !value) return value
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function StepReview({ formData, onEdit }) {
  return (
    <>
      <h2 className="quote__title">Review your request</h2>
      <p className="quote__hint">
        Check the details below. You can go back and change anything before
        submitting.
      </p>

      <div className="review">
        {GROUPS.map((group) => (
          <section className="review__group" key={group.step}>
            <div className="review__group-head">
              <h3>{group.title}</h3>
              <button
                className="review__edit"
                type="button"
                onClick={() => onEdit(group.step)}
              >
                Edit<span className="sr-only"> {group.title.toLowerCase()}</span>
              </button>
            </div>
            <dl className="review__rows">
              {group.rows.map((row) => {
                const raw = formData[row.field]
                const value = formatValue(row.field, raw)

                return (
                  <div className="review__row" key={row.field}>
                    <dt>{row.label}</dt>
                    <dd className={value ? '' : 'is-empty'}>
                      {value || 'Not provided'}
                    </dd>
                  </div>
                )
              })}
            </dl>
          </section>
        ))}
      </div>
    </>
  )
}
