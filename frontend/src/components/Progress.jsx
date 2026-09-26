import { STEPS } from '../data/content.js'

export function Progress({ currentStep }) {
  const percent = ((currentStep - 1) / (STEPS.length - 1)) * 100
  const current = STEPS.find((step) => step.number === currentStep)

  return (
    <div className="progress">
      <div className="progress__meta">
        <span className="progress__step-label">Step {currentStep} of {STEPS.length}</span>
        <span>{current?.label}</span>
      </div>

      <div
        className="progress__bar"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={STEPS.length}
        aria-valuenow={currentStep}
        aria-valuetext={`Step ${currentStep} of ${STEPS.length}: ${current?.label}`}
      >
        <div className="progress__bar-fill" style={{ width: `${percent}%` }} />
      </div>

      <ol className="progress__steps">
        {STEPS.map((step) => {
          const state =
            step.number === currentStep
              ? 'current'
              : step.number < currentStep
                ? 'done'
                : 'todo'

          return (
            <li
              key={step.number}
              className={`progress__step progress__step--${state}`}
              aria-current={state === 'current' ? 'step' : undefined}
            >
              <span className="progress__dot" aria-hidden="true">
                {step.number}
              </span>
              <span className="progress__step-label">{step.label}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
