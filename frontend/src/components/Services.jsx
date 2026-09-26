import { SERVICES } from '../data/content.js'
import { ServiceVisual } from './ServiceVisual.jsx'

export function Services() {
  return (
    <section className="section section--off-white" id="services">
      <div className="container">
        <div className="section-heading">
          <p className="eyebrow">Services</p>
          <h2>Cleaning and facility support, scoped to your site</h2>
          <p>
            Five service lines covering the routine, the restorative and the
            reactive — combined under one agreement and one point of contact.
          </p>
        </div>

        <div className="services__grid">
          {SERVICES.map((service, index) => (
            <article className="service-card" key={service.id}>
              <ServiceVisual
                variant={service.visual}
                label={String(index + 1).padStart(2, '0')}
              />
              <div className="service-card__body">
                <span className="service-card__index">
                  {String(index + 1).padStart(2, '0')} / 05
                </span>
                <h3>{service.name}</h3>
                <p>{service.summary}</p>
                <p className="service-card__detail">{service.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
