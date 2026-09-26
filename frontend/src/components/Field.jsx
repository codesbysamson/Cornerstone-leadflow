/**
 * Accessible field wrapper. Links the label, hint and error message to the
 * control via ids/aria-describedby, and marks invalid state for assistive tech.
 *
 * `id` must be supplied by the caller so it stays stable across renders —
 * a generated counter would change the association on every render.
 */
export function Field({ id, label, hint, error, optional = false, children }) {
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}{' '}
        {optional ? <span className="field__optional">(optional)</span> : null}
      </label>
      {hint ? (
        <p className="field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {children({ id, describedBy, invalid: Boolean(error) })}
      {error ? (
        <p className="field__error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
