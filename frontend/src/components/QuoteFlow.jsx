import { useCallback, useRef, useState } from 'react'

import { STEPS } from '../data/content.js'
import { createLead } from '../lib/api.js'
import { validateAll, validateStep } from '../lib/validation.js'
import { Progress } from './Progress.jsx'
import { StepService } from './steps/StepService.jsx'
import { StepProperty } from './steps/StepProperty.jsx'
import { StepRequirements } from './steps/StepRequirements.jsx'
import { StepContact } from './steps/StepContact.jsx'
import { StepReview } from './steps/StepReview.jsx'
import { QuoteSuccess } from './QuoteSuccess.jsx'

const EMPTY_FORM = {
  service: '',
  property_type: '',
  location: '',
  property_size: '',
  frequency: '',
  preferred_date: '',
  requirements: '',
  customer_name: '',
  email: '',
  phone: '',
}

const STEP_COMPONENTS = {
  1: StepService,
  2: StepProperty,
  3: StepRequirements,
  4: StepContact,
  5: StepReview,
}

const FIRST_STEP = 1
const LAST_STEP = STEPS.length
const REVIEW_STEP = LAST_STEP

export function QuoteFlow({ onExit }) {
  const [step, setStep] = useState(FIRST_STEP)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [status, setStatus] = useState('idle') // idle | submitting | done
  const [createdLead, setCreatedLead] = useState(null)

  // Belt-and-braces alongside the disabled button: prevents a second POST even
  // if the click lands before React re-renders.
  const submittingRef = useRef(false)
  const headingRef = useRef(null)

  const handleChange = useCallback((field, value) => {
    setFormData((current) => ({ ...current, [field]: value }))
    setErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }, [])

  const goToStep = (nextStep) => {
    setStep(nextStep)
    setSubmitError('')
    // Move focus to the new step heading for screen reader and keyboard users.
    window.requestAnimationFrame(() => headingRef.current?.focus())
  }

  const handleBack = () => {
    if (step <= FIRST_STEP) return
    setErrors({})
    goToStep(step - 1)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (submittingRef.current) return

    // The primary control is a single type="submit" button for every step, so
    // the button never changes type underneath the user's click. Before the
    // review step it only advances; the enquiry is posted on review only.
    if (step < REVIEW_STEP) {
      const stepErrors = validateStep(step, formData)
      if (Object.keys(stepErrors).length > 0) {
        setErrors(stepErrors)
        return
      }
      setErrors({})
      goToStep(step + 1)
      return
    }

    const allErrors = validateAll(formData)
    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors)
      // Send the user to the earliest step that still needs attention.
      const firstBadStep = [1, 2, 4].find(
        (candidate) => validateStep(candidate, formData) &&
          Object.keys(validateStep(candidate, formData)).length > 0,
      )
      if (firstBadStep) goToStep(firstBadStep)
      return
    }

    submittingRef.current = true
    setStatus('submitting')
    setSubmitError('')

    try {
      const lead = await createLead({
        service: formData.service,
        property_type: formData.property_type,
        location: formData.location,
        property_size: formData.property_size || null,
        frequency: formData.frequency || null,
        preferred_date: formData.preferred_date || null,
        requirements: formData.requirements || null,
        customer_name: formData.customer_name,
        email: formData.email,
        phone: formData.phone,
      })

      setCreatedLead(lead)
      setStatus('done')
    } catch (error) {
      // Form data is intentionally left intact so the customer can retry.
      setSubmitError(error.message)
      if (error.fields && Object.keys(error.fields).length > 0) {
        setErrors((current) => ({ ...current, ...error.fields }))
      }
      setStatus('idle')
    } finally {
      submittingRef.current = false
    }
  }

  if (status === 'done' && createdLead) {
    return (
      <QuoteSuccess
        lead={createdLead}
        formData={formData}
        onReturnHome={onExit}
        onStartAnother={() => {
          setFormData(EMPTY_FORM)
          setErrors({})
          setSubmitError('')
          setCreatedLead(null)
          setStatus('idle')
          setStep(FIRST_STEP)
        }}
      />
    )
  }

  const StepComponent = STEP_COMPONENTS[step]
  const isReview = step === REVIEW_STEP
  const isSubmitting = status === 'submitting'

  return (
    <form className="quote" onSubmit={handleSubmit} noValidate>
      <Progress currentStep={step} />

      <div className="quote__body">
        <h1 className="sr-only" ref={headingRef} tabIndex={-1}>
          Request a quote — step {step} of {LAST_STEP}
        </h1>

        {submitError ? (
          <div className="quote__alert" role="alert">
            <div className="quote__alert-body">
              <strong>Your request was not submitted</strong>
              <p>{submitError}</p>
            </div>
          </div>
        ) : null}

        <div aria-live="polite">
          <StepComponent
            formData={formData}
            errors={errors}
            onChange={handleChange}
            onEdit={goToStep}
          />
        </div>
      </div>

      <div className="quote__footer">
        <button
          className="btn btn--secondary"
          type="button"
          onClick={handleBack}
          disabled={step === FIRST_STEP || isSubmitting}
        >
          Back
        </button>

        <p className="quote__footer-note">
          {isReview
            ? 'Submitting records your request as a structured enquiry.'
            : `Step ${step} of ${LAST_STEP}`}
        </p>

        {isReview ? (
          <button className="btn btn--primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <span className="btn__spinner" aria-hidden="true" />
                Submitting
              </>
            ) : (
              'Submit request'
            )}
          </button>
        ) : (
          <button className="btn btn--primary" type="submit" disabled={isSubmitting}>
            Continue
          </button>
        )}
      </div>
    </form>
  )
}
