import { useState } from 'react'

import { crossSiteWarning, login } from '../../lib/authApi.js'

/**
 * The staff sign-in screen.
 *
 * The failure message is the one the API returns, verbatim and unspecific: it
 * says the email or password is wrong, never which. Distinguishing "no such
 * account" here would turn this form into a way to discover who works for the
 * company, so the message is deliberately vague and this screen does not try to
 * improve on it.
 */
export function LoginScreen({ onSignedIn, onExit }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  // A development misconfiguration, not a credential problem. Login would
  // succeed and every request afterwards would 401, so it is called out
  // separately from the sign-in error.
  const configWarning = crossSiteWarning()

  async function handleSubmit(event) {
    event.preventDefault()
    if (busy) return

    setError(null)
    setBusy(true)

    try {
      const user = await login(email.trim(), password)
      // The password is dropped from component state the moment it is no
      // longer needed, rather than left in memory for the rest of the session.
      setPassword('')
      onSignedIn(user)
    } catch (caught) {
      setError(caught.message)
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="crm-login">
      <div className="crm-login__panel">
        <span className="crm__mark" aria-hidden="true" />

        <h1 className="crm-login__title">Staff sign in</h1>
        <p className="crm-login__subtitle">
          Apex LeadFlow is for the internal team. Customer enquiries do not need
          an account.
        </p>

        {configWarning ? (
          <p className="crm-login__warning" role="status">
            {configWarning}
          </p>
        ) : null}

        <form className="crm-login__form" onSubmit={handleSubmit} noValidate>
          <label className="crm-login__field">
            <span className="crm-login__label">Work email</span>
            <input
              type="email"
              name="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              // Not disabled while busy: a mis-typed email should be
              // correctable, and the field is cheap to re-render.
            />
          </label>

          <label className="crm-login__field">
            <span className="crm-login__label">Password</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error ? (
            <p className="crm-login__error" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            className="crm-login__submit"
            disabled={busy || !email || !password}
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <button type="button" className="crm-login__exit" onClick={onExit}>
          Back to the website
        </button>
      </div>
    </div>
  )
}
