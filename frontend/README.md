# CarePath — Care Navigation & Assessment

CarePath is a clinical decision-support and care navigation platform for care managers conducting patient phone assessments and managing patient panels.

---

## How to Run the Project Locally

### Prerequisites
Make sure you have **Node.js** (v18 or higher) and **npm** installed on your system.

---

### Step 1: Open Terminal & Navigate to Project Folder
Open your command prompt, PowerShell, or terminal and navigate to the project directory:

```bash
cd UIUX_CTS
```

---

### Step 2: Install Dependencies
Install all required npm packages:

```bash
npm install --legacy-peer-deps
```

---

### Step 3: Start the Development Server
Run the local Vite development server:

```bash
npm run dev
```

After running this command, open your web browser and go to:

👉 **[http://localhost:3000](http://localhost:3000)** *(or http://localhost:3001 if port 3000 is occupied)*

---

## Production Build & Testing

To test or verify the production bundle:

```bash
npm run build
```

---

## Project Structure Overview

```
UIUX_CTS/
├── app/
│   ├── components/
│   │   ├── app-shell.tsx         # Sidebar navigation & layout shell
│   │   ├── status-badge.tsx      # Patient status indicator badge
│   │   └── ui/                   # Shadcn UI primitives (Button, Select, RadioGroup, etc.)
│   ├── routes/
│   │   ├── __root.tsx            # Root layout route
│   │   ├── index.tsx             # Root redirect route
│   │   ├── care-assessment.tsx   # Care Assessment call workflow (/care-assessment)
│   │   ├── follow-ups.tsx        # Follow-ups tracking page (/follow-ups)
│   │   ├── my-care.tsx           # Patient care options view (/my-care)
│   │   ├── providers.tsx         # Service providers directory (/providers)
│   │   └── patients/
│   │       ├── index.tsx         # All Patients panel dashboard (/patients)
│   │       └── $patientId.tsx    # Single Patient Detail & Assessment history (/patients/$patientId)
│   ├── lib/
│   │   ├── care-store.ts         # In-memory reactive state & assessment actions
│   │   ├── mock-data.ts          # Patient & provider dataset
│   │   └── utils.ts              # Styling utilities
│   ├── routeTree.gen.ts          # Auto-generated TanStack Router tree
│   ├── router.tsx                # Router configuration
│   ├── main.tsx                  # Client entry point
│   └── styles.css                # Tailwind CSS v4 styling & tokens
├── public/                       # Static assets
├── package.json                  # NPM packages and scripts
├── tsconfig.json                 # TypeScript path aliases (@/* -> ./app/*)
└── vite.config.ts                # Vite & TanStack Router configuration
```

---

## Available Pages & Features

- **All Patients (`/patients`)**: Filter and search through panel patients, historical ED visits, and suggested outreach.
- **Care Assessment (`/care-assessment`)**: Fast, structured workspace for care managers talking to a patient on a normal phone. Enter Patient ID (e.g. `p-1042` or `MRN 480-1042`), review historical context, record current call details, and save assessment.
- **Patient Detail (`/patients/$patientId`)**: View utilization timeline, flagging reasons, and previously recorded Care Assessments with option to start a new assessment.
- **Providers (`/providers`)**: View available primary care, urgent care, telehealth, and care management providers in the service area.
- **Follow-ups (`/follow-ups`)**: Track contacted patients and next scheduled actions.
