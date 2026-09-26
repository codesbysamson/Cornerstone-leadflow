const NAV_LINKS = [
  { href: '#services', label: 'Services' },
  { href: '#how-it-works', label: 'How It Works' },
  { href: '#why-apex', label: 'Why Apex' },
]

export function Footer({ onStartQuote }) {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__top">
          <div className="footer__about">
            <a className="brand" href="#top">
              <span className="brand__mark" aria-hidden="true" />
              <span className="brand__text">
                <span className="brand__name">Apex Facility Services</span>
                <span className="brand__sub">Commercial &amp; Facilities</span>
              </span>
            </a>
            <p>
              Commercial cleaning and facility support for workplaces and
              managed properties.
            </p>
          </div>

          <nav className="footer__nav" aria-label="Footer">
            <h2>Explore</h2>
            <ul>
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
              <li>
                <button type="button" onClick={onStartQuote}>
                  Request a Quote
                </button>
              </li>
            </ul>
          </nav>
        </div>

        <div className="footer__bottom">
          <p className="footer__disclaimer">
            Apex Facility Services is a fictional company created for the
            Cornerstone LeadFlow software demonstration. The services described
            here are illustrative and no real premises, clients or
            accreditations are represented.
          </p>
        </div>
      </div>
    </footer>
  )
}
