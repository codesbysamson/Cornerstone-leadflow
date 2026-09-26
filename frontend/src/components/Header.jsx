import { useState } from 'react'

const LINKS = [
  { href: '#services', label: 'Services' },
  { href: '#how-it-works', label: 'How It Works' },
  { href: '#why-apex', label: 'Why Apex' },
]

export function Header({ onStartQuote }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const startQuote = () => {
    setMenuOpen(false)
    onStartQuote()
  }

  return (
    <header className="header">
      <div className="container header__inner">
        <a className="brand" href="#top">
          <span className="brand__mark" aria-hidden="true" />
          <span className="brand__text">
            <span className="brand__name">Apex Facility Services</span>
            <span className="brand__sub">Commercial &amp; Facilities</span>
          </span>
        </a>

        <button
          className="nav__toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? 'Close' : 'Menu'}
        </button>

        <nav
          className="nav__panel"
          id="primary-navigation"
          aria-label="Primary"
          data-open={menuOpen ? 'true' : 'false'}
        >
          {LINKS.map((link) => (
            <a
              className="nav__link"
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <button
            className="btn btn--primary nav__cta"
            type="button"
            onClick={startQuote}
          >
            Request a Quote
          </button>
        </nav>
      </div>
    </header>
  )
}
