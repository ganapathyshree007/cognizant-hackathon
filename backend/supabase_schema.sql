-- Supabase Schema for UC07 Care Manager Application

-- 1. Profiles Table (Linked to auth.users)
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('CARE_MANAGER', 'PATIENT')),
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS for profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public profiles are viewable by authenticated users." ON public.profiles FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Users can insert their own profile." ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile." ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 2. Patients Table (Links a Profile ID to an EHR Patient ID)
-- This allows patient login -> their profile -> their EHR records
CREATE TABLE public.patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) UNIQUE, -- Can be null if patient doesn't have an account yet
    patient_id TEXT UNIQUE NOT NULL, -- EHR Patient ID
    phone TEXT UNIQUE,
    name TEXT,
    demographics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;
-- Patients can see their own data. Care Managers can see all patients.
CREATE POLICY "Patients see own record" ON public.patients FOR SELECT USING (
    auth.uid() = profile_id OR 
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);
CREATE POLICY "Care Managers can insert/update patients" ON public.patients FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);

-- 3. Encounters Table (Historical/Active Encounters)
CREATE TABLE public.encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id TEXT UNIQUE NOT NULL,
    patient_id TEXT REFERENCES public.patients(patient_id) NOT NULL,
    date TIMESTAMP WITH TIME ZONE,
    description TEXT,
    status TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.encounters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients see own encounters" ON public.encounters FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.patients WHERE patient_id = public.encounters.patient_id AND profile_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);

-- 4. Appointments Table
CREATE TABLE public.appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id TEXT UNIQUE NOT NULL,
    patient_id TEXT REFERENCES public.patients(patient_id) NOT NULL,
    encounter_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    provider_npi TEXT,
    pac_id TEXT,
    provider_specialty TEXT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'Scheduled',
    care_manager_id UUID REFERENCES public.profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients see own appointments" ON public.appointments FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.patients WHERE patient_id = public.appointments.patient_id AND profile_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);
CREATE POLICY "Care Managers can insert/update appointments" ON public.appointments FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);

-- 5. Outcomes Table (Post-Consultation)
CREATE TABLE public.outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id TEXT UNIQUE NOT NULL,
    appointment_id TEXT REFERENCES public.appointments(appointment_id) NOT NULL,
    patient_id TEXT REFERENCES public.patients(patient_id) NOT NULL,
    encounter_id TEXT NOT NULL,
    clinical_notes TEXT,
    diagnoses TEXT,
    follow_up_required BOOLEAN DEFAULT false,
    consultation_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.outcomes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Patients see own outcomes" ON public.outcomes FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.patients WHERE patient_id = public.outcomes.patient_id AND profile_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);
CREATE POLICY "Care Managers can insert/update outcomes" ON public.outcomes FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);

-- 6. Audit Trail Table
CREATE TABLE public.audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    patient_id TEXT,
    encounter_id TEXT,
    reviewer_id UUID REFERENCES public.profiles(id),
    action TEXT NOT NULL,
    reason TEXT,
    system_pathway TEXT,
    system_provider TEXT,
    selected_provider TEXT,
    details JSONB
);

ALTER TABLE public.audit_trail ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Only Care Managers can view audit logs" ON public.audit_trail FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);
CREATE POLICY "Care Managers can insert audit logs" ON public.audit_trail FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'CARE_MANAGER')
);

-- Helper functions and triggers for auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (new.id, new.raw_user_meta_data->>'full_name', COALESCE(new.raw_user_meta_data->>'role', 'PATIENT'));
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
