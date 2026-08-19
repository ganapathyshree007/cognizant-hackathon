import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { 
  UserPlus, X, HeartPulse, Activity, AlertCircle, 
  Sparkles, CheckCircle2, ChevronRight, User, Stethoscope, ShieldCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "../routes/__root";

interface AddPatientModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPatientAdded?: (patient: any) => void;
}

export function AddPatientModal({ open, onOpenChange, onPatientAdded }: AddPatientModalProps) {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState<"demographics" | "history" | "vitals">("demographics");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    // Demographics
    patientId: "",
    firstName: "",
    lastName: "",
    age: 45,
    gender: "F",
    race: "white",
    ethnicity: "nonhispanic",
    maritalStatus: "M",
    state: "Massachusetts",
    phone: "",
    // Clinical History
    chronicConditions: "",
    activeMedicationsCount: 1,
    medicationsList: "",
    emergency30d: 0,
    inpatient30d: 0,
    outpatient30d: 1,
    emergency365d: 0,
    inpatient365d: 0,
    // Presenting Intake
    chiefComplaint: "",
    temperature: "98.6",
    heartRate: "72",
    systolicBP: "120",
    spo2: "99",
    respRate: "16",
    pain: "0"
  });

  if (!open) return null;

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const generateRandomId = () => {
    const randomHex = Math.random().toString(36).substring(2, 10);
    setFormData(prev => ({ ...prev, patientId: `pt-${randomHex}` }));
  };

  const handleSubmit = async (andStartAssessment = false) => {
    setIsSubmitting(true);
    try {
      const token = session?.access_token || "mock-token-123";
      const payload = {
        patient_id: formData.patientId.trim() || undefined,
        first_name: formData.firstName.trim() || "Patient",
        last_name: formData.lastName.trim() || "",
        age_at_index: Number(formData.age) || 45,
        gender: formData.gender,
        race: formData.race,
        ethnicity: formData.ethnicity,
        marital_status: formData.maritalStatus,
        state: formData.state,
        emergency_30d: Number(formData.emergency30d) || 0,
        inpatient_30d: Number(formData.inpatient30d) || 0,
        outpatient_30d: Number(formData.outpatient30d) || 0,
        emergency_365d: Number(formData.emergency365d) || 0,
        inpatient_365d: Number(formData.inpatient365d) || 0,
        hist_active_condition_count: formData.chronicConditions ? 2 : 1,
        hist_chronic_condition_count: formData.chronicConditions ? 1 : 0,
        hist_active_medication_count: Number(formData.activeMedicationsCount) || 1,
        primary_condition: formData.chronicConditions,
        medications: formData.medicationsList,
        chief_complaint: formData.chiefComplaint,
        initial_vitals: {
          Temperature: formData.temperature,
          "Heart Rate": formData.heartRate,
          "Systolic BP": formData.systolicBP,
          SpO2: formData.spo2,
          "Respiratory Rate": formData.respRate,
          Pain: formData.pain
        }
      };

      const response = await fetch("/api/patients", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const text = await response.text();
      let result: any = {};
      try {
        result = text ? JSON.parse(text) : {};
      } catch {
        result = { message: text };
      }

      if (!response.ok) {
        throw new Error(result.detail || result.message || `Server error (${response.status})`);
      }

      toast.success(`Patient ${result.patient_id} created successfully!`);
      onOpenChange(false);

      if (onPatientAdded) {
        onPatientAdded(result);
      }

      if (andStartAssessment) {
        navigate({
          to: "/care-assessment",
          search: {
            patientId: result.patient_id,
            encounterId: result.encounter_id
          }
        });
      }
    } catch (err: any) {
      console.error("Failed to add patient:", err);
      toast.error(err.message || "Failed to create patient record");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-2xl rounded-2xl bg-card border border-border shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2.5">
            <div className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold">
              <UserPlus className="size-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">Add New Patient Intake</h2>
              <p className="text-xs text-muted-foreground">Register patient demographics and initial EHR features</p>
            </div>
          </div>
          <button 
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border bg-muted/10 px-6 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("demographics")}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "demographics"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <User className="size-3.5" /> 1. Demographics
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "history"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Activity className="size-3.5" /> 2. Clinical History
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("vitals")}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "vitals"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <HeartPulse className="size-3.5" /> 3. Intake Vitals (Optional)
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {activeTab === "demographics" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="patientId" className="text-xs">Patient ID / MRN</Label>
                    <button 
                      type="button" 
                      onClick={generateRandomId}
                      className="text-[11px] text-primary hover:underline flex items-center gap-1 font-medium"
                    >
                      <Sparkles className="size-3" /> Auto-generate
                    </button>
                  </div>
                  <Input 
                    id="patientId"
                    placeholder="e.g. pt-9a4f2c81 (auto-generates if empty)"
                    value={formData.patientId}
                    onChange={e => handleChange("patientId", e.target.value)}
                    className="font-mono text-xs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="firstName" className="text-xs">First Name</Label>
                    <Input 
                      id="firstName"
                      placeholder="Jane"
                      value={formData.firstName}
                      onChange={e => handleChange("firstName", e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="lastName" className="text-xs">Last Name</Label>
                    <Input 
                      id="lastName"
                      placeholder="Doe"
                      value={formData.lastName}
                      onChange={e => handleChange("lastName", e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="age" className="text-xs">Age at Index</Label>
                  <Input 
                    id="age"
                    type="number"
                    min="1"
                    max="120"
                    value={formData.age}
                    onChange={e => handleChange("age", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="gender" className="text-xs">Gender</Label>
                  <select 
                    id="gender"
                    className="w-full rounded-md border border-input bg-card px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={formData.gender}
                    onChange={e => handleChange("gender", e.target.value)}
                  >
                    <option value="F">Female (F)</option>
                    <option value="M">Male (M)</option>
                    <option value="O">Other</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="maritalStatus" className="text-xs">Marital Status</Label>
                  <select 
                    id="maritalStatus"
                    className="w-full rounded-md border border-input bg-card px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={formData.maritalStatus}
                    onChange={e => handleChange("maritalStatus", e.target.value)}
                  >
                    <option value="M">Married (M)</option>
                    <option value="S">Single (S)</option>
                    <option value="D">Divorced (D)</option>
                    <option value="W">Widowed (W)</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="state" className="text-xs">State</Label>
                  <Input 
                    id="state"
                    placeholder="Massachusetts"
                    value={formData.state}
                    onChange={e => handleChange("state", e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="race" className="text-xs">Race</Label>
                  <select 
                    id="race"
                    className="w-full rounded-md border border-input bg-card px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={formData.race}
                    onChange={e => handleChange("race", e.target.value)}
                  >
                    <option value="white">White</option>
                    <option value="black">Black / African American</option>
                    <option value="asian">Asian</option>
                    <option value="native">American Indian / Alaska Native</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ethnicity" className="text-xs">Ethnicity</Label>
                  <select 
                    id="ethnicity"
                    className="w-full rounded-md border border-input bg-card px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={formData.ethnicity}
                    onChange={e => handleChange("ethnicity", e.target.value)}
                  >
                    <option value="nonhispanic">Non-Hispanic</option>
                    <option value="hispanic">Hispanic or Latino</option>
                  </select>
                </div>
              </div>

              <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground flex items-center justify-between">
                <span>Next step: Configure historical baseline risk & previous encounters</span>
                <Button 
                  type="button" 
                  size="sm" 
                  variant="outline" 
                  onClick={() => setActiveTab("history")}
                  className="gap-1 text-xs h-7"
                >
                  Next <ChevronRight className="size-3" />
                </Button>
              </div>
            </div>
          )}

          {activeTab === "history" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="space-y-1.5">
                <Label htmlFor="chronicConditions" className="text-xs">Known Chronic Conditions / Diagnoses</Label>
                <Input 
                  id="chronicConditions"
                  placeholder="e.g. Hypertension, Type 2 Diabetes, Mild Asthma"
                  value={formData.chronicConditions}
                  onChange={e => handleChange("chronicConditions", e.target.value)}
                />
                <p className="text-[11px] text-muted-foreground">Used to populate LightGBM active condition features</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="medicationsList" className="text-xs">Current Active Medications</Label>
                  <Input 
                    id="medicationsList"
                    placeholder="e.g. Lisinopril 10mg, Metformin 500mg"
                    value={formData.medicationsList}
                    onChange={e => handleChange("medicationsList", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="activeMedsCount" className="text-xs">Active Medication Count</Label>
                  <Input 
                    id="activeMedsCount"
                    type="number"
                    min="0"
                    max="50"
                    value={formData.activeMedicationsCount}
                    onChange={e => handleChange("activeMedicationsCount", e.target.value)}
                  />
                </div>
              </div>

              <div className="border-t border-border pt-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Historical Utilization (EHR 44-Feature Weights)
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">ED Visits (30d)</Label>
                    <Input 
                      type="number" 
                      min="0" 
                      value={formData.emergency30d}
                      onChange={e => handleChange("emergency30d", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">Inpatient (30d)</Label>
                    <Input 
                      type="number" 
                      min="0" 
                      value={formData.inpatient30d}
                      onChange={e => handleChange("inpatient30d", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">ED Visits (365d)</Label>
                    <Input 
                      type="number" 
                      min="0" 
                      value={formData.emergency365d}
                      onChange={e => handleChange("emergency365d", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px] text-muted-foreground">Inpatient (365d)</Label>
                    <Input 
                      type="number" 
                      min="0" 
                      value={formData.inpatient365d}
                      onChange={e => handleChange("inpatient365d", e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground flex items-center justify-between">
                <span>Optional: Record presenting vitals or jump straight to intake</span>
                <Button 
                  type="button" 
                  size="sm" 
                  variant="outline" 
                  onClick={() => setActiveTab("vitals")}
                  className="gap-1 text-xs h-7"
                >
                  Vitals <ChevronRight className="size-3" />
                </Button>
              </div>
            </div>
          )}

          {activeTab === "vitals" && (
            <div className="space-y-4 animate-in fade-in duration-150">
              <div className="space-y-1.5">
                <Label htmlFor="chiefComplaint" className="text-xs">Chief Complaint / Intake Call Note</Label>
                <Input 
                  id="chiefComplaint"
                  placeholder="e.g. Mild chest discomfort, routine medication check, following up on discharge"
                  value={formData.chiefComplaint}
                  onChange={e => handleChange("chiefComplaint", e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">Temperature (°F)</Label>
                  <Input 
                    value={formData.temperature}
                    onChange={e => handleChange("temperature", e.target.value)}
                    placeholder="98.6"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Heart Rate (bpm)</Label>
                  <Input 
                    value={formData.heartRate}
                    onChange={e => handleChange("heartRate", e.target.value)}
                    placeholder="72"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Systolic BP (mmHg)</Label>
                  <Input 
                    value={formData.systolicBP}
                    onChange={e => handleChange("systolicBP", e.target.value)}
                    placeholder="120"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">SpO2 (%)</Label>
                  <Input 
                    value={formData.spo2}
                    onChange={e => handleChange("spo2", e.target.value)}
                    placeholder="99"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Resp Rate (/min)</Label>
                  <Input 
                    value={formData.respRate}
                    onChange={e => handleChange("respRate", e.target.value)}
                    placeholder="16"
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Pain Score (0-10)</Label>
                  <Input 
                    type="number"
                    min="0"
                    max="10"
                    value={formData.pain}
                    onChange={e => handleChange("pain", e.target.value)}
                    className="text-xs"
                  />
                </div>
              </div>

              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
                <ShieldCheck className="size-4 shrink-0 text-emerald-600" />
                <span>Deterministic Safety Gate will automatically evaluate these vitals upon starting assessment.</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/20">
          <Button 
            type="button" 
            variant="ghost" 
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
            className="text-xs"
          >
            Cancel
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleSubmit(false)}
              disabled={isSubmitting}
              className="text-xs"
            >
              Save Patient Only
            </Button>
            <Button
              type="button"
              onClick={() => handleSubmit(true)}
              disabled={isSubmitting}
              className="text-xs gap-1.5 bg-primary font-medium"
            >
              {isSubmitting ? "Saving..." : "Save & Start Assessment"}
              <ChevronRight className="size-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
