/**
 * Client-side validation.
 *
 * This intentionally mirrors only what the backend's LeadCreate schema
 * requires. Optional fields are never blocked, and the email rule stays
 * deliberately loose so it does not reject addresses the API would accept.
 */

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

const TRIMMED = (value) => (typeof value === 'string' ? value.trim() : '')

export const STEP_FIELDS = {
  1: ['service'],
  2: ['property_type', 'location'],
  3: [],
  4: ['customer_name', 'email', 'phone'],
  5: [],
}

function fieldError(field, value) {
  const v = TRIMMED(value)

  switch (field) {
    case 'service':
      return v ? '' : 'Select the service you need.'
    case 'property_type':
      return v ? '' : 'Select the type of property.'
    case 'location':
      return v ? '' : 'Enter the property location.'
    case 'customer_name':
      return v ? '' : 'Enter your name.'
    case 'email':
      if (!v) return 'Enter your email address.'
      return EMAIL_PATTERN.test(v)
        ? ''
        : 'Enter a valid email address, for example name@company.com.'
    case 'phone':
      return v ? '' : 'Enter a contact phone number.'
    default:
      return ''
  }
}

/** Returns { field: message } for the given step; empty object means valid. */
export function validateStep(step, formData) {
  const errors = {}

  for (const field of STEP_FIELDS[step] ?? []) {
    const message = fieldError(field, formData[field])
    if (message) errors[field] = message
  }

  return errors
}

/** Guards the final submit across every step. */
export function validateAll(formData) {
  return [1, 2, 4].reduce(
    (errors, step) => ({ ...errors, ...validateStep(step, formData) }),
    {},
  )
}
