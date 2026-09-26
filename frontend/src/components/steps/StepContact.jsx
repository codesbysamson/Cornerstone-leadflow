import { Field } from '../Field.jsx'

export function StepContact({ formData, errors, onChange }) {
  return (
    <>
      <h2 className="quote__title">Your contact details</h2>
      <p className="quote__hint">
        So we can review the requirements and come back to you about the
        quotation.
      </p>

      <div className="quote__fields">
        <Field id="customer_name" label="Full name" error={errors.customer_name}>
          {({ id, describedBy, invalid }) => (
            <input
              id={id}
              className="input"
              type="text"
              autoComplete="name"
              placeholder="Sarah Johnson"
              value={formData.customer_name}
              aria-describedby={describedBy}
              aria-invalid={invalid || undefined}
              onChange={(event) => onChange('customer_name', event.target.value)}
            />
          )}
        </Field>

        <div className="field-row">
          <Field id="email" label="Email address" error={errors.email}>
            {({ id, describedBy, invalid }) => (
              <input
                id={id}
                className="input"
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="name@company.com"
                value={formData.email}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => onChange('email', event.target.value)}
              />
            )}
          </Field>

          <Field id="phone" label="Phone number" error={errors.phone}>
            {({ id, describedBy, invalid }) => (
              <input
                id={id}
                className="input"
                type="tel"
                autoComplete="tel"
                placeholder="+44 7700 900123"
                value={formData.phone}
                aria-describedby={describedBy}
                aria-invalid={invalid || undefined}
                onChange={(event) => onChange('phone', event.target.value)}
              />
            )}
          </Field>
        </div>
      </div>
    </>
  )
}
