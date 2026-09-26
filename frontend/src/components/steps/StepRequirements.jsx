import { Field } from '../Field.jsx'

const PROMPTS = [
  'Access restrictions, keys or security passes',
  'Times the building is occupied',
  'Areas that need specialist treatment',
  'Scope that is not covered by the standard service',
]

export function StepRequirements({ formData, onChange }) {
  return (
    <>
      <h2 className="quote__title">Any special requirements?</h2>
      <p className="quote__hint">
        This is where the detail that affects the quote belongs. The more
        specific you are, the more accurate the quotation can be.
      </p>

      <div className="quote__fields">
        <Field
          id="requirements"
          label="Requirements"
          optional
          hint="Cleaning required outside normal office hours."
        >
          {({ id, describedBy }) => (
            <textarea
              id={id}
              className="textarea"
              rows={8}
              placeholder="Describe the site, the access arrangements and anything we should plan for."
              value={formData.requirements}
              aria-describedby={describedBy}
              onChange={(event) => onChange('requirements', event.target.value)}
            />
          )}
        </Field>
      </div>

      <div className="prompt-box">
        <p className="prompt-box__title">Useful to mention</p>
        <ul className="prompt-box__list">
          {PROMPTS.map((prompt) => (
            <li key={prompt}>{prompt}</li>
          ))}
        </ul>
      </div>
    </>
  )
}
