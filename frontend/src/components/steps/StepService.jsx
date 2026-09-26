import { SERVICES } from '../../data/content.js'

export function StepService({ formData, errors, onChange }) {
  return (
    <>
      <h2 className="quote__title">What service do you need?</h2>
      <p className="quote__hint">
        Choose the closest match. If your requirement spans more than one, pick
        the primary service and describe the rest in step three.
      </p>

      <fieldset
        className="choice-list"
        aria-describedby={errors.service ? 'service-error' : undefined}
      >
        <legend className="sr-only">Service required</legend>

        {SERVICES.map((service) => {
          const selected = formData.service === service.name

          return (
            <label
              className={`choice${selected ? ' choice--selected' : ''}`}
              key={service.id}
            >
              <input
                type="radio"
                name="service"
                value={service.name}
                checked={selected}
                aria-invalid={errors.service ? 'true' : undefined}
                onChange={() => onChange('service', service.name)}
              />
              <span className="choice__body">
                <span className="choice__title">{service.name}</span>
                <span className="choice__desc">{service.summary}</span>
              </span>
            </label>
          )
        })}
      </fieldset>

      {errors.service ? (
        <p className="field__error" id="service-error" role="alert">
          {errors.service}
        </p>
      ) : null}
    </>
  )
}
