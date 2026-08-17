export type CareType = "Primary Care" | "Urgent Care" | "Telehealth" | "Care Management";

export type PatientStatus = "Needs review" | "Outreach sent" | "Scheduled" | "Closed";

export type CareManagerAssessmentOption =
  | "Emergency evaluation"
  | "Same-day care"
  | "Routine primary care / follow-up"
  | "Clinician review";

export type CareAssessmentRecord = {
  assessment_id: string;
  patient_id: string;
  date_time: string;
  patient_description: string;
  main_concern: string;
  concern_details?: string;
  onset: string;
  worsening: "Yes" | "No" | "Unsure";
  additional_notes?: string;
  care_manager_assessment: CareManagerAssessmentOption;
  recommended_pathway: string;
  status: "Completed";
};

export type Patient = {
  id: string;
  name: string;
  age: number;
  mrn: string;
  edVisits6mo: number;
  pattern: string;
  suggested: CareType;
  status: PatientStatus;
  reasons: string[];
  timeline: { month: string; visits: number }[];
  lastContact?: string;
  nextAction?: string;
  assessments?: CareAssessmentRecord[];
};

export const patients: Patient[] = [
  {
    id: "p-1042",
    name: "Marcus Bell",
    age: 46,
    mrn: "MRN 480-1042",
    edVisits6mo: 5,
    pattern: "Repeat evening visits, low-acuity discharge",
    suggested: "Primary Care",
    status: "Needs review",
    reasons: [
      "Five ED encounters in the last six months, four discharged the same day.",
      "No primary care visit recorded in the last 14 months.",
      "Three visits occurred after 7pm, when the assigned clinic was closed.",
      "Documented conditions are typically managed in an office setting.",
    ],
    timeline: [
      { month: "Mar", visits: 1 },
      { month: "Apr", visits: 0 },
      { month: "May", visits: 1 },
      { month: "Jun", visits: 1 },
      { month: "Jul", visits: 0 },
      { month: "Aug", visits: 2 },
    ],
    assessments: [
      {
        assessment_id: "asm-101",
        patient_id: "p-1042",
        date_time: "Aug 02, 2026, 14:15",
        patient_description: "Patient called regarding mild evening cough and medication refill questions.",
        main_concern: "Medication",
        onset: "2–3 days ago",
        worsening: "No",
        additional_notes: "Patient advised clinic hours for routine refills.",
        care_manager_assessment: "Routine primary care / follow-up",
        recommended_pathway: "Primary Care",
        status: "Completed",
      },
    ],
  },
  {
    id: "p-1130",
    name: "Alina Okafor",
    age: 33,
    mrn: "MRN 480-1130",
    edVisits6mo: 4,
    pattern: "Weekend visits for recurring upper-respiratory concerns",
    suggested: "Urgent Care",
    status: "Needs review",
    reasons: [
      "Four ED encounters in six months, all on weekends.",
      "Two urgent care sites within 3 miles were open at the time of visit.",
      "No follow-up appointment recorded after the last two encounters.",
    ],
    timeline: [
      { month: "Mar", visits: 0 },
      { month: "Apr", visits: 1 },
      { month: "May", visits: 1 },
      { month: "Jun", visits: 0 },
      { month: "Jul", visits: 1 },
      { month: "Aug", visits: 1 },
    ],
    assessments: [],
  },
  {
    id: "p-1188",
    name: "Robert Chen",
    age: 61,
    mrn: "MRN 480-1188",
    edVisits6mo: 6,
    pattern: "Chronic condition flare-ups between appointments",
    suggested: "Care Management",
    status: "Outreach sent",
    lastContact: "Aug 12, 2026",
    nextAction: "Confirm care plan review call",
    reasons: [
      "Six ED encounters in six months tied to a chronic condition.",
      "Gaps of more than 90 days between scheduled specialist visits.",
      "Medication refill history shows interruptions before three encounters.",
      "Patient is not currently enrolled in a care management program.",
    ],
    timeline: [
      { month: "Mar", visits: 1 },
      { month: "Apr", visits: 1 },
      { month: "May", visits: 2 },
      { month: "Jun", visits: 0 },
      { month: "Jul", visits: 1 },
      { month: "Aug", visits: 1 },
    ],
    assessments: [
      {
        assessment_id: "asm-102",
        patient_id: "p-1188",
        date_time: "Jul 28, 2026, 09:30",
        patient_description: "Reported mild joint swelling and requested chronic care navigation details.",
        main_concern: "Follow-up",
        onset: "More than a week ago",
        worsening: "No",
        additional_notes: "Follow-up outreach scheduled.",
        care_manager_assessment: "Routine primary care / follow-up",
        recommended_pathway: "Care Management",
        status: "Completed",
      },
    ],
  },
  {
    id: "p-1204",
    name: "Denise Hartley",
    age: 52,
    mrn: "MRN 480-1204",
    edVisits6mo: 3,
    pattern: "Daytime visits, transportation barriers noted",
    suggested: "Telehealth",
    status: "Scheduled",
    lastContact: "Aug 9, 2026",
    nextAction: "Telehealth intake Aug 20",
    reasons: [
      "Three ED encounters in six months, all during clinic hours.",
      "Transportation barrier documented in two intake notes.",
      "Concerns raised were consistent with remote-eligible follow-up.",
    ],
    timeline: [
      { month: "Mar", visits: 0 },
      { month: "Apr", visits: 1 },
      { month: "May", visits: 0 },
      { month: "Jun", visits: 1 },
      { month: "Jul", visits: 0 },
      { month: "Aug", visits: 1 },
    ],
    assessments: [],
  },
  {
    id: "p-1256",
    name: "Javier Ruiz",
    age: 28,
    mrn: "MRN 480-1256",
    edVisits6mo: 4,
    pattern: "New to area, no established primary care",
    suggested: "Primary Care",
    status: "Needs review",
    reasons: [
      "Four ED encounters since relocating to the service area.",
      "No assigned primary care provider on file.",
      "Two encounters were for routine prescription continuation.",
    ],
    timeline: [
      { month: "Mar", visits: 0 },
      { month: "Apr", visits: 0 },
      { month: "May", visits: 1 },
      { month: "Jun", visits: 1 },
      { month: "Jul", visits: 1 },
      { month: "Aug", visits: 1 },
    ],
    assessments: [],
  },
  {
    id: "p-1301",
    name: "Grace Lindqvist",
    age: 70,
    mrn: "MRN 480-1301",
    edVisits6mo: 2,
    pattern: "Post-discharge follow-up gaps",
    suggested: "Care Management",
    status: "Closed",
    lastContact: "Jul 28, 2026",
    nextAction: "No further action",
    reasons: [
      "Two ED encounters within 30 days of an inpatient discharge.",
      "Follow-up appointment was scheduled but not attended.",
      "Home support needs noted during discharge planning.",
    ],
    timeline: [
      { month: "Mar", visits: 0 },
      { month: "Apr", visits: 0 },
      { month: "May", visits: 1 },
      { month: "Jun", visits: 0 },
      { month: "Jul", visits: 1 },
      { month: "Aug", visits: 0 },
    ],
    assessments: [],
  },
];

export type Provider = {
  id: string;
  name: string;
  careType: CareType;
  location: string;
  distanceMiles: number;
  availability: string;
};

export const providers: Provider[] = [
  {
    id: "pr-1",
    name: "Riverbend Family Medicine",
    careType: "Primary Care",
    location: "1180 Chestnut St, Springfield",
    distanceMiles: 1.2,
    availability: "Next opening Aug 19",
  },
  {
    id: "pr-2",
    name: "Northside Community Health",
    careType: "Primary Care",
    location: "42 Halsted Ave, Springfield",
    distanceMiles: 2.8,
    availability: "Next opening Aug 24",
  },
  {
    id: "pr-3",
    name: "Cedar Street Urgent Care",
    careType: "Urgent Care",
    location: "77 Cedar St, Springfield",
    distanceMiles: 0.9,
    availability: "Walk-in, 8am–10pm daily",
  },
  {
    id: "pr-4",
    name: "Westgate Urgent Care",
    careType: "Urgent Care",
    location: "2200 Westgate Blvd, Springfield",
    distanceMiles: 3.4,
    availability: "Walk-in, 9am–9pm daily",
  },
  {
    id: "pr-5",
    name: "CarePath Virtual Clinic",
    careType: "Telehealth",
    location: "Video visit",
    distanceMiles: 0,
    availability: "Same-day, 7am–11pm",
  },
  {
    id: "pr-6",
    name: "Nurse Line — 24/7 Advice",
    careType: "Telehealth",
    location: "Phone visit",
    distanceMiles: 0,
    availability: "Available 24/7",
  },
  {
    id: "pr-7",
    name: "Population Health Care Team",
    careType: "Care Management",
    location: "Springfield Health Network",
    distanceMiles: 4.1,
    availability: "Intake within 3 business days",
  },
  {
    id: "pr-8",
    name: "Chronic Care Navigators",
    careType: "Care Management",
    location: "310 Lake Rd, Springfield",
    distanceMiles: 5.6,
    availability: "Intake within 1 week",
  },
];

export const SAFETY_NOTE =
  "This recommendation is based on historical utilization and does not determine whether a current condition is an emergency. If you are experiencing severe or life-threatening symptoms, seek emergency care.";
