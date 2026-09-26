import { HOW_IT_WORKS } from '../data/content.js'

export function HowItWorks() {
  return (
    <section className="section section--paper" id="how-it-works">
      <div className="container">
        <div className="section-heading">
          <p className="eyebrow">How it works</p>
          <h2>A quotation built from a documented brief</h2>
          <p>
            We do not quote from a phone call. Your request is captured as a
            structured set of requirements first, so the quotation can be
            scoped to the property rather than guessed at.
          </p>
        </div>

        <ol className="steps-flow">
          {HOW_IT_WORKS.map((step) => (
            <li className="steps-flow__item" key={step.number}>
              <span className="steps-flow__number">Step {step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
