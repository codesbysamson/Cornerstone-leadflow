import { WHY_APEX } from '../data/content.js'

export function WhyApex() {
  return (
    <section className="section section--dark" id="why-apex">
      <div className="container">
        <div className="section-heading">
          <p className="eyebrow">Why Apex</p>
          <h2>Operational discipline, not promises</h2>
          <p>
            What follows is how the work is organised. It is the part of a
            service contract that determines whether the result is consistent
            month to month.
          </p>
        </div>

        <div className="why__grid">
          {WHY_APEX.map((item) => (
            <article className="why__item" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
