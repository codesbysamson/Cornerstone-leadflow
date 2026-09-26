export const SERVICES = [
  {
    id: 'office-cleaning',
    name: 'Office Cleaning',
    summary:
      'Scheduled daily, weekly or out-of-hours cleaning for office floors, workstations, washrooms and shared areas.',
    detail:
      'Covered daily tasks, washroom consumables, waste handling and periodic rotation across desk zones, washrooms and communal areas.',
    visual: 'office',
  },
  {
    id: 'deep-cleaning',
    name: 'Deep Cleaning',
    summary:
      'A thorough restorative clean for areas that routine schedules cannot reach, planned around your operating hours.',
    detail:
      'High-level dusting, skirting, internal glass, hard-floor treatment and detailed washroom work, delivered as a one-off or seasonal programme.',
    visual: 'deep',
  },
  {
    id: 'move-in-move-out',
    name: 'Move-In / Move-Out Cleaning',
    summary:
      'End-of-tenancy and handover cleaning, scoped to the condition schedule a landlord or agent expects.',
    detail:
      'Full void cleans including appliances, inside cabinets, tracks, and a documented condition report suitable for handover or re-letting.',
    visual: 'move',
  },
  {
    id: 'facility-maintenance',
    name: 'Facility Maintenance',
    summary:
      'Planned and reactive maintenance coordination for managed properties, handled through the same request channel.',
    detail:
      'First-line response coordination, planned preventative visits, and contractor supervision recorded against the same site history.',
    visual: 'facility',
  },
  {
    id: 'commercial-cleaning',
    name: 'Commercial Cleaning',
    summary:
      'Larger contracts across multi-tenant and industrial sites, with named supervision and scheduled reporting.',
    detail:
      'Multi-site and out-of-hours programmes with named site supervisors, documented inspections and consolidated service reporting.',
    visual: 'commercial',
  },
]

export const SERVICE_OPTIONS = SERVICES.map((service) => service.name)

export const PROPERTY_TYPES = [
  'Office',
  'Warehouse / Industrial',
  'Retail Unit',
  'Multi-tenant Building',
  'Clinic / Medical',
  'Education',
  'Residential Block',
  'Other',
]

export const FREQUENCIES = [
  'One-off',
  'Daily',
  'Weekly',
  'Fortnightly',
  'Monthly',
  'To be confirmed',
]

export const STEPS = [
  { number: 1, label: 'Service' },
  { number: 2, label: 'Property' },
  { number: 3, label: 'Requirements' },
  { number: 4, label: 'Contact' },
  { number: 5, label: 'Review' },
]

export const HOW_IT_WORKS = [
  {
    number: '01',
    title: 'Tell us what you need',
    body: 'Use the quote request to describe your service, property, location and any special requirements. Every field maps directly to what our team reviews.',
  },
  {
    number: '02',
    title: 'We review the requirements',
    body: 'Your request is captured as a structured enquiry rather than an unstructured message, so scope, access and scheduling details are all in one place.',
  },
  {
    number: '03',
    title: 'Receive your tailored quote',
    body: 'Once the requirements have been reviewed, we come back with a quotation scoped to your property and the arrangements you need.',
  },
]

export const WHY_APEX = [
  {
    title: 'Structured service planning',
    body: 'Work is scoped before it is scheduled. Tasks, areas and frequencies are agreed in advance so the service is delivered the same way each visit.',
  },
  {
    title: 'Flexible scheduling',
    body: 'Out-of-hours, early-morning and weekend arrangements are planned around how your building is actually used, not just our operating hours.',
  },
  {
    title: 'Clear communication',
    body: 'One channel for service issues, changes and additional scope. Requests are recorded and visible rather than passed between people.',
  },
  {
    title: 'Requirements captured first',
    body: 'We quote from a documented brief — property, size, frequency and access — so the quotation reflects the site and the standard agreed.',
  },
]
