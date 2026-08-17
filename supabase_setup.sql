-- 1. Create profiles table that mirrors auth.users
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT,
    full_name TEXT,
    role TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for profiles but allow public read for now, and insert from trigger
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public profiles are viewable by everyone." ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can insert their own profile." ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Trigger function to copy user data on signup
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    new.id, 
    new.email, 
    new.raw_user_meta_data->>'full_name', 
    new.raw_user_meta_data->>'role'
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 2. Create appointments table
CREATE TABLE IF NOT EXISTS public.appointments (
    appointment_id TEXT PRIMARY KEY,
    patient_id TEXT,
    encounter_id TEXT,
    provider_name TEXT,
    provider_npi TEXT,
    pac_id TEXT,
    provider_specialty TEXT,
    appointment_date TEXT,
    appointment_time TEXT,
    status TEXT,
    care_manager_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create outcomes table
CREATE TABLE IF NOT EXISTS public.outcomes (
    outcome_id TEXT PRIMARY KEY,
    appointment_id TEXT,
    patient_id TEXT,
    encounter_id TEXT,
    clinical_notes TEXT,
    follow_up_required BOOLEAN,
    consultation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create patient_features table
CREATE TABLE IF NOT EXISTS public.patient_features (
    "PATIENT_ID" TEXT,
    "ENCOUNTER_ID" TEXT,
    "INDEX_TIMESTAMP" TEXT,
    "age_at_index" REAL,
    "gender" TEXT,
    "race" TEXT,
    "ethnicity" TEXT,
    "marital_status" TEXT,
    "state" TEXT,
    "all_encounters_30d" INTEGER,
    "emergency_30d" INTEGER,
    "inpatient_30d" INTEGER,
    "outpatient_30d" INTEGER,
    "ambulatory_30d" INTEGER,
    "urgent_care_30d" INTEGER,
    "wellness_30d" INTEGER,
    "total_encounter_cost_30d" REAL,
    "all_encounters_90d" INTEGER,
    "emergency_90d" INTEGER,
    "inpatient_90d" INTEGER,
    "outpatient_90d" INTEGER,
    "ambulatory_90d" INTEGER,
    "urgent_care_90d" INTEGER,
    "wellness_90d" INTEGER,
    "total_encounter_cost_90d" REAL,
    "all_encounters_365d" INTEGER,
    "emergency_365d" INTEGER,
    "inpatient_365d" INTEGER,
    "outpatient_365d" INTEGER,
    "ambulatory_365d" INTEGER,
    "urgent_care_365d" INTEGER,
    "wellness_365d" INTEGER,
    "total_encounter_cost_365d" REAL,
    "days_since_previous_encounter" INTEGER,
    "days_since_previous_ed" INTEGER,
    "days_since_last_inpatient" INTEGER,
    "days_since_last_outpatient" INTEGER,
    "hist_condition_count" INTEGER,
    "hist_unique_condition_count" INTEGER,
    "hist_active_condition_count" INTEGER,
    "hist_chronic_condition_count" INTEGER,
    "hist_medication_count" INTEGER,
    "hist_medication_diversity" INTEGER,
    "hist_active_medication_count" INTEGER,
    "hist_procedure_count" INTEGER,
    "hist_unique_procedure_count" INTEGER,
    "hist_careplan_count" INTEGER
);

-- Audit trail (already exists per original code, but ensuring it's here)
CREATE TABLE IF NOT EXISTS public.audit_trail (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    patient_id TEXT,
    encounter_id TEXT,
    reviewer_id TEXT,
    action TEXT,
    reason TEXT,
    system_pathway TEXT,
    system_provider TEXT,
    selected_provider TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
