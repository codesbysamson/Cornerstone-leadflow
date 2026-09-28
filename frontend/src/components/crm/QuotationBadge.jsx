import { quotationStatusMeta } from '../../data/quotation.js'

/** Renders a quotation status, falling back to neutral styling if unknown. */
export function QuotationBadge({ status }) {
  const { label, tone } = quotationStatusMeta(status)
  return <span className={`crm-badge crm-badge--q-${tone}`}>{label}</span>
}
