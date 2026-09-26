/**
 * Illustrative placeholder treatment in place of service photography.
 * Rendered entirely in CSS so the demo carries no stock imagery and makes no
 * implied claim about real Apex sites.
 */
export function ServiceVisual({ variant, label }) {
  return (
    <div className={`visual visual--${variant}`} aria-hidden="true">
      <span className="visual__label">{label}</span>
      <span className="visual__glyph">
        {variant.charAt(0).toUpperCase()}
      </span>
    </div>
  )
}
