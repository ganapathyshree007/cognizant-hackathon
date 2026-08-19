-- ============================================================
-- patient_vitals table — run this in Supabase SQL Editor
-- Links to: audit_trail, appointments via patient_id + encounter_id
-- ============================================================

CREATE TABLE IF NOT EXISTS public.patient_vitals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys (join to backend_files, appointments, audit_trail)
    patient_id              TEXT NOT NULL,
    encounter_id            TEXT NOT NULL,
    assessed_at             TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL,

    -- Vitals
    temperature_c           NUMERIC(5,2),
    heart_rate              NUMERIC(6,1),
    spo2                    NUMERIC(5,1),
    systolic_bp             NUMERIC(6,1),
    respiratory_rate        NUMERIC(5,1),
    pain_level              NUMERIC(4,1),

    -- Clinical context flags
    avpu                    TEXT,
    chest_pain              BOOLEAN,
    bleeding                BOOLEAN,
    convulsions             BOOLEAN,
    allergic_reaction       BOOLEAN,
    active_high_risk        BOOLEAN,

    -- Symptoms
    symptoms_text           TEXT,
    selected_symptoms       TEXT[],
    extracted_features      JSONB,

    -- Safety Gate output (from /api/evaluate)
    safety_status           TEXT,
    safety_rule_triggered   TEXT,
    safety_reason           TEXT,

    -- ML Risk output (Step 4)
    risk_band               TEXT,
    risk_score              NUMERIC(6,4),

    -- Care Pathway (Step 6)
    pathway_code            TEXT,
    pathway_name            TEXT,

    -- Metadata
    care_manager_id         UUID,
    raw_clinical_context    JSONB,

    created_at              TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- Fast lookup indexes
CREATE INDEX IF NOT EXISTS idx_pv_patient_id   ON public.patient_vitals(patient_id);
CREATE INDEX IF NOT EXISTS idx_pv_encounter_id ON public.patient_vitals(encounter_id);
CREATE INDEX IF NOT EXISTS idx_pv_assessed_at  ON public.patient_vitals(assessed_at DESC);

-- RLS (service role bypasses this; anon/authenticated users see nothing unless explicitly granted)
ALTER TABLE public.patient_vitals ENABLE ROW LEVEL SECURITY;

-- Allow service role (backend) to insert freely
CREATE POLICY "Backend service role can insert vitals"
    ON public.patient_vitals
    FOR INSERT
    WITH CHECK (true);

-- Allow Care Managers (authenticated users) to read
CREATE POLICY "Care Managers can read patient vitals"
    ON public.patient_vitals
    FOR SELECT
    USING (true);

-- ============================================================
-- Also add care_manager_notes column to appointments if needed
-- ============================================================
ALTER TABLE public.appointments
    ADD COLUMN IF NOT EXISTS care_manager_notes TEXT;
