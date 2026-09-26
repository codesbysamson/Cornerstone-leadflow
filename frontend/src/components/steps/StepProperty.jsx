import { Field } from '../Field.jsx'
import { FREQUENCIES, PROPERTY_TYPES } from '../../data/content.js'

export function StepProperty({ formData, errors, onChange }) {
  const today = new Date().toISOString().slice(0, 10)

  return (
    <>
      <h2 className="quote__title">Tell us about the property</h2>
      <p className="quote__hint">
        This is what the quotation is built from — property type, location, size
        and how often you need the service.
      </p>

      <div className="quote__fields">
        <div className="field-row">
          <Field id="property_type" label="Property type" error={errors.property_type}>
            {({ id, describedBy, invalid }) => (
              <select
                id={id}
                className="select"
                value={formData.property_type}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => onChange('property_type', event.target.value)}
              >
                <option value="">Select a property type</option>
                {PROPERTY_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            )}
          </Field>

          <Field id="location" label="Location" error={errors.location}>
            {({ id, describedBy, invalid }) => (
              <input
                id={id}
                className="input"
                type="text"
                autoComplete="address-level2"
                placeholder="City or town"
                value={formData.location}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => onChange('location', event.target.value)}
              />
            )}
          </Field>
        </div>

        <div className="field-row">
          <Field
            id="property_size"
            label="Approximate size"
            optional
            hint="Floor area, number of units or number of desks."
          >
            {({ id, describedBy }) => (
              <input
                id={id}
                className="input"
                type="text"
                placeholder="e.g. 2,500 sq ft"
                value={formData.property_size}
                aria-describedby={describedBy}
                onChange={(event) => onChange('property_size', event.target.value)}
              />
            )}
          </Field>

          <Field id="frequency" label="Frequency" optional>
            {({ id, describedBy }) => (
              <select
                id={id}
                className="select"
                value={formData.frequency}
                aria-describedby={describedBy}
                onChange={(event) => onChange('frequency', event.target.value)}
              >
                <option value="">Select a frequency</option>
                {FREQUENCIES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            )}
          </Field>
        </div>

        <Field
          id="preferred_date"
          label="Preferred start date"
          optional
          hint="An indicative date is fine."
        >
          {({ id, describedBy }) => (
            <input
              id={id}
              className="input"
              type="date"
              min={today}
              value={formData.preferred_date}
              aria-describedby={describedBy}
              onChange={(event) => onChange('preferred_date', event.target.value)}
            />
          )}
        </Field>
      </div>
    </>
  )
}
