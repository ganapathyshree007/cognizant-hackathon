import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  CheckCircle2, ShieldAlert, AlertTriangle, UserCheck, 
  Activity, Calendar, Download, Search, Thermometer, HeartPulse, ShieldCheck, Sparkles, ArrowLeft, ChevronRight
} from "lucide-react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AddPatientModal } from "@/components/add-patient-modal";
import { toast } from "sonner";
import { useAuth } from "./__root";
import { apiUrl } from "@/lib/api";

type SearchParams = { patientId?: string; encounterId?: string; };

export const Route = createFileRoute("/care-assessment")({
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    patientId: typeof search.patientId === "string" ? search.patientId : undefined,
    encounterId: typeof search.encounterId === "string" ? search.encounterId : undefined,
  }),
  head: () => ({ meta: [{ title: "Care Assessment — CarePath" }] }),
  component: CareAssessmentPage,
});

const PROGRESS_STEPS = ["Patient Context", "Symptoms", "Measurements", "Safety Gate", "Care Pathway", "Provider Match", "Appointment Booking"];

function CareAssessmentPage() {
  const navigate = useNavigate();
  const searchParams = Route.useSearch();
  const { session } = useAuth();
  
  const paramPatientId = searchParams.patientId;
  const paramEncounterId = searchParams.encounterId;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [explanation, setExplanation] = useState<string | null>(null);

  // Symptom Inputs
  const [selectedCommonSymptoms, setSelectedCommonSymptoms] = useState<string[]>([]);
  const [symptomsText, setSymptomsText] = useState("");
  const [processingSymptoms, setProcessingSymptoms] = useState(false);
  const [extractedFeatures, setExtractedFeatures] = useState<Record<string, any>>({});

  // Vitals Grid State
  const [clinicalForm, setClinicalForm] = useState<Record<string, string>>({
    "Temperature": "", "Heart Rate": "", "SpO2": "", "Systolic BP": "", "Respiratory Rate": "", "Pain": ""
  });
  const [notAvailable, setNotAvailable] = useState<Record<string, boolean>>({});

  // Context Fields
  const [contextFields, setContextFields] = useState<Record<string, string>>({
    "AVPU": "", "Chest Pain": "", "Bleeding": "", "Convulsions": "", "Allergic Reaction": "", "Active High-Risk Condition": ""
  });

  const [auditReason, setAuditReason] = useState("");
  const [approved, setApproved] = useState(false);
  const [apptForm, setApptForm] = useState({ date: "", time: "", selectedProviderIndex: 0 });

  const buildFinalContext = () => {
    const ctx: any = { ...extractedFeatures };
    // Add Vitals
    Object.keys(clinicalForm).forEach(key => {
      if (!notAvailable[key] && clinicalForm[key] !== "") ctx[key] = clinicalForm[key];
    });
    // Add Context Fields
    Object.keys(contextFields).forEach(key => {
      if (contextFields[key] !== "") {
        const val = contextFields[key];
        if (val === "Yes") ctx[key] = true;
        else if (val === "No") ctx[key] = false;
        else ctx[key] = val;
      }
    });
    // Add common symptoms selected
    selectedCommonSymptoms.forEach(sym => ctx[sym] = true);
    return ctx;
  };

  // State for Patient Picker when no patient is selected
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerPatients, setPickerPatients] = useState<any[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [addPatientOpen, setAddPatientOpen] = useState(false);

  useEffect(() => {
    if (!paramPatientId) {
      const fetchPickerPatients = async () => {
        setPickerLoading(true);
        try {
          const token = session?.access_token || "mock-token-123";
          const res = await fetch(apiUrl(`/api/patients/search?query=${encodeURIComponent(pickerSearch)}`), {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const text = await res.text();
            const data = text ? JSON.parse(text) : [];
            setPickerPatients(data);
          }
        } catch (e) {
          console.warn("Picker search error:", e);
        } finally {
          setPickerLoading(false);
        }
      };
      fetchPickerPatients();
    }
  }, [paramPatientId, pickerSearch, session]);

  const fetchPatientData = async (pid: string, eid: string, isStage2 = false, contextOverride = null) => {
    const token = session?.access_token || "mock-token-123";
    setLoading(true); 
    setError(null);
    if (!isStage2) { 
      setData(null); 
      setExplanation(null); 
      setApproved(false); 
      setSymptomsText(""); 
      setSelectedCommonSymptoms([]); 
    }
    
    let contextToSend: any = {};
    if (isStage2) {
      contextToSend = contextOverride || buildFinalContext();
    }
    
    try {
      const response = await fetch(apiUrl('/api/evaluate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ patient_id: pid, encounter_id: eid || "UNKNOWN", clinical_context: contextToSend })
      });

      const text = await response.text();
      let result: any = {};
      try {
        result = text ? JSON.parse(text) : {};
      } catch {
        throw new Error(`Server returned non-JSON response (${response.status})`);
      }

      if (!response.ok || result?.error) {
        setError(result || { message: `Server error (${response.status})`, error: "SERVER_ERROR" });
      } else {
        setData(result);
        if (isStage2 && result.step5?.status !== "PENDING") {
          fetchExplanation(result, contextToSend);
        }
      }
    } catch (e: any) { 
      setError({ message: e.message || "Failed to connect to evaluation engine", error: "CONNECTION_ERROR" }); 
    } finally {
      setLoading(false);
    }
  };

  const fetchExplanation = async (resultData: any, contextToSend: any) => {
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/explain'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          step4: resultData.step4 || {}, 
          step5: resultData.step5 || {},
          step6: resultData.step6 || {}, 
          step7: resultData.step7 || {},
          clinical_context: contextToSend 
        })
      });
      if (response.ok) {
        const text = await response.text();
        const expRes = text ? JSON.parse(text) : {};
        if (expRes.explanation) setExplanation(expRes.explanation);
      }
    } catch (e) { 
      console.error("fetchExplanation error:", e); 
    }
  };

  useEffect(() => {
    if (paramPatientId) {
      fetchPatientData(paramPatientId, paramEncounterId || "UNKNOWN", false);
    }
  }, [paramPatientId, paramEncounterId, session]);

  const extractSymptoms = async () => {
    if (!symptomsText.trim()) return;
    setProcessingSymptoms(true);
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/symptoms/llm-extract'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ symptoms: symptomsText })
      });
      if (response.ok) {
        const text = await response.text();
        const result = text ? JSON.parse(text) : {};
        if (result.status === "success") {
          setExtractedFeatures(result.extracted_features);
          toast.success("AI extracted clinical features");
        }
      } else {
        toast.error("Could not parse symptoms automatically. You can select features manually.");
      }
    } catch (e) { 
      toast.error("Error connecting to symptoms extraction API"); 
    } finally {
      setProcessingSymptoms(false);
    }
  };

  const evaluateCondition = async () => {
    if (symptomsText.trim() && Object.keys(extractedFeatures).length === 0) {
      await extractSymptoms();
    }
    const finalContext = buildFinalContext();
    await fetchPatientData(paramPatientId!, paramEncounterId || "UNKNOWN", true, finalContext);
    toast.success("Evaluation completed with deterministic Safety Gate");
  };

  const handleDecision = async (action: string) => {
    if ((action === "REJECT" || action === "ESCALATE") && !auditReason) {
      toast.error(`A reason is required to ${action.toLowerCase()}.`);
      return;
    }
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/audit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          patient_id: paramPatientId, 
          encounter_id: paramEncounterId || "UNKNOWN", 
          action: action, 
          reason: auditReason || "Approved",
          system_pathway: data?.step6?.Pathway || "N/A", 
          system_provider: data?.step7?.Options?.[0]?.Name || "NONE",
          selected_provider: data?.step7?.Options?.[0]?.Name || "NONE"
        })
      });
      if (response.ok) { 
        setAuditReason(""); 
        if (action === "APPROVE") setApproved(true);
        toast.success(`Decision "${action}" recorded in audit trail`);
      }
    } catch (e) { 
      toast.error("Error saving audit trail"); 
    }
  };

  const handleScheduleAppt = async () => {
    if (!apptForm.date || !apptForm.time) {
      toast.error("Please select date and time.");
      return;
    }
    const provider = data.step7.Options[apptForm.selectedProviderIndex];
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/appointments'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          patient_id: paramPatientId, 
          encounter_id: paramEncounterId || "UNKNOWN", 
          provider_name: provider.Name, 
          provider_npi: String(provider.NPI || "N/A"), 
          pac_id: String(provider.PAC_ID || "N/A"),
          provider_specialty: provider.Specialty, 
          appointment_date: apptForm.date, 
          appointment_time: apptForm.time
        })
      });
      if (response.ok) { 
        toast.success("Appointment scheduled successfully!"); 
        navigate({ to: "/follow-ups" }); 
      }
    } catch (e) { 
      toast.error("Failed to schedule appointment"); 
    }
  };

  const currentStepIndex = approved ? 6 : data?.step7?.Status === "SUCCESS" ? 5 : data?.step6 ? 4 : data?.step5?.status && data.step5.status !== "PENDING" ? 3 : data?.step4 ? 1 : 0;

  if (!paramPatientId) {
    return (
      <AppShell>
        <AddPatientModal 
          open={addPatientOpen} 
          onOpenChange={setAddPatientOpen}
          onPatientAdded={(newPt) => {
            navigate({
              to: "/care-assessment",
              search: { patientId: newPt.patient_id, encounterId: newPt.encounter_id }
            });
          }}
        />

        <Breadcrumbs items={[
          { label: "Dashboard", to: "/" },
          { label: "Care Assessment" },
        ]} />
        
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Care Assessment Workflow</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Select an existing patient record or register a new intake to begin the clinical orchestration protocol.
            </p>
          </div>
          <Button 
            onClick={() => setAddPatientOpen(true)} 
            className="gap-2 shrink-0 bg-primary font-medium"
          >
            <UserCheck className="size-4" /> + Add New Patient
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left / Main: Search & Pick Patient */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-card rounded-xl border border-border p-5 shadow-xs">
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  placeholder="Search by Patient ID (e.g. 00126cb9, pt-...) or leave empty to view recent..."
                  className="pl-9"
                />
              </div>

              <div className="overflow-hidden rounded-lg border border-border">
                <table className="w-full text-xs table-fixed">
                  <thead>
                    <tr className="bg-muted/40 text-muted-foreground text-left border-b border-border">
                      <th className="px-3.5 py-2.5 font-medium w-[45%]">Patient Name & ID</th>
                      <th className="px-3.5 py-2.5 font-medium w-[25%]">DOB / Age</th>
                      <th className="px-3.5 py-2.5 font-medium w-[15%]">Gender</th>
                      <th className="px-3.5 py-2.5 font-medium w-[15%] text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {pickerLoading ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground animate-pulse">
                          Loading patients...
                        </td>
                      </tr>
                    ) : pickerPatients.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                          No patients found. Click "+ Add New Patient" to register a patient.
                        </td>
                      </tr>
                    ) : (
                      pickerPatients.slice(0, 8).map((p, idx) => (
                        <tr key={idx} className="hover:bg-muted/30 transition-colors">
                          <td className="px-3.5 py-2.5 min-w-0">
                            <div className="font-semibold text-foreground truncate" title={p.full_name}>
                              {p.full_name || `Patient ${p.PATIENT_ID.substring(0, 8)}`}
                            </div>
                            <div className="font-mono text-[10px] text-muted-foreground truncate" title={p.PATIENT_ID}>
                              {p.PATIENT_ID}
                            </div>
                          </td>
                          <td className="px-3.5 py-2.5 text-muted-foreground truncate">
                            <span className="text-foreground font-medium">{p.dob || "1985-04-12"}</span>
                            <span className="ml-1 text-[11px]">({p.age_at_index}y)</span>
                          </td>
                          <td className="px-3.5 py-2.5 text-muted-foreground">
                            {p.gender === "M" ? "Male" : p.gender === "F" ? "Female" : p.gender}
                          </td>
                          <td className="px-3.5 py-2.5 text-right">
                            <Button
                              size="sm"
                              className="h-7 text-xs gap-1 px-2.5"
                              onClick={() => {
                                navigate({
                                  to: "/care-assessment",
                                  search: { patientId: p.PATIENT_ID, encounterId: p.ENCOUNTER_ID || "UNKNOWN" }
                                });
                              }}
                            >
                              Start <ChevronRight className="size-3" />
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Right: Quick Instructions & Actions */}
          <div className="space-y-4">
            <div className="bg-card rounded-xl border border-border p-5 shadow-xs space-y-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sparkles className="size-4 text-primary" /> Orchestration Guide
              </h3>
              <ul className="space-y-2.5 text-xs text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="font-bold text-primary">1.</span>
                  <span><strong>Step 4 ML Risk:</strong> Evaluates 44 historical EHR features with LightGBM ensemble model.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-primary">2.</span>
                  <span><strong>Step 5 Safety Gate:</strong> Deterministic clinical rule validation on vitals & red flags.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-primary">3.</span>
                  <span><strong>Step 6 Pathway & Step 7 Provider Match:</strong> Automated clinical alignment and instant scheduling.</span>
                </li>
              </ul>
              
              <div className="pt-2 border-t border-border">
                <Button 
                  variant="outline" 
                  className="w-full text-xs" 
                  onClick={() => navigate({ to: "/patients" })}
                >
                  Browse Full Patient Database
                </Button>
              </div>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients", to: "/patients" },
        { label: `Patient ${paramPatientId?.substring(0, 8)}`, to: `/patients/${paramPatientId}` },
        { label: "Care Assessment" },
      ]} />

      {/* Sticky Progress Header */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-4 mb-8 sticky top-0 z-10">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div>
            <h1 className="text-lg font-semibold">Care Assessment</h1>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">Patient: {paramPatientId} · Encounter: {paramEncounterId || "UNKNOWN"}</p>
          </div>
          <div className="flex gap-1 overflow-x-auto max-w-full pb-1">
            {PROGRESS_STEPS.map((step, idx) => (
              <div key={idx} className={`flex items-center whitespace-nowrap text-xs font-medium px-2 py-1 rounded-full ${
                idx === currentStepIndex ? "bg-primary text-primary-foreground" : idx < currentStepIndex ? "bg-primary/10 text-primary" : "text-muted-foreground"
              }`}>
                {step} {idx < PROGRESS_STEPS.length - 1 && <span className="ml-2 opacity-50">→</span>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          <AlertTriangle className="size-5 shrink-0" />
          <span>{error.message || (typeof error === 'string' ? error : (error.detail || JSON.stringify(error)))}</span>
        </div>
      )}
      
      {loading && !data && <div className="p-12 text-center text-muted-foreground animate-pulse">Running Step 4 ML Model on 44 Features...</div>}

      {data && (
        <div className="flex flex-col lg:flex-row gap-8">
          {/* LEFT COLUMN: Data Entry & Workflow */}
          <div className="flex-1 space-y-8 min-w-0">
            
            {/* SYMPTOMS SECTION */}
            <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
              <div className="bg-muted/20 px-6 py-4 border-b border-border">
                <h2 className="font-semibold flex items-center gap-2"><Activity className="w-4 h-4 text-primary" /> Current Symptoms</h2>
              </div>
              <div className="p-6 space-y-6">
                
                {/* Common Symptoms Multi-Select */}
                <div>
                  <Label className="mb-2 block text-sm">Common Symptoms (Select multiple)</Label>
                  <select 
                    onChange={(e) => {
                      const val = e.target.value;
                      if(val && !selectedCommonSymptoms.includes(val)) setSelectedCommonSymptoms([...selectedCommonSymptoms, val]);
                      e.target.value = "";
                    }}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
                  >
                    <option value="">Select a symptom to add...</option>
                    <option value="No current symptoms">No current symptoms</option>
                    <option value="Fever">Fever</option>
                    <option value="Cough">Cough</option>
                    <option value="Chest Pain">Chest Pain</option>
                    <option value="Shortness of breath">Shortness of breath</option>
                    <option value="Headache">Headache</option>
                    <option value="Fatigue">Fatigue</option>
                    <option value="Nausea">Nausea</option>
                  </select>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {selectedCommonSymptoms.map(sym => (
                      <span key={sym} className="inline-flex items-center gap-1 bg-secondary text-secondary-foreground text-xs px-2.5 py-1 rounded-full">
                        {sym} <button onClick={() => setSelectedCommonSymptoms(selectedCommonSymptoms.filter(s => s !== sym))} className="hover:text-destructive text-muted-foreground ml-1">×</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Describe Symptoms Natural Language */}
                <div>
                  <Label className="mb-2 block text-sm">Describe Symptoms (Free-Text)</Label>
                  <textarea 
                    value={symptomsText}
                    onChange={(e) => setSymptomsText(e.target.value)}
                    placeholder="Describe what the patient is experiencing..."
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm min-h-[100px]"
                  />
                  <div className="flex justify-end mt-2">
                    <Button variant="secondary" size="sm" onClick={extractSymptoms} disabled={processingSymptoms || !symptomsText.trim()}>
                      {processingSymptoms ? "Extracting features..." : "Extract Features with LLM"}
                    </Button>
                  </div>
                </div>

                {/* AI Extracted Features Block */}
                {Object.keys(extractedFeatures).length > 0 && (
                  <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                    <h4 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">AI Detected Clinical Features</h4>
                    <ul className="text-sm list-disc pl-5 space-y-1 text-foreground">
                      {Object.keys(extractedFeatures).map(k => (
                        <li key={k}>{k}: <span className="text-muted-foreground">{String(extractedFeatures[k])}</span></li>
                      ))}
                    </ul>
                    <p className="text-xs text-muted-foreground mt-3 italic">Note: The AI layer only extracts terms. The deterministic Safety Gate evaluates them.</p>
                  </div>
                )}
              </div>
            </section>

            {/* MEASUREMENTS SECTION */}
            <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
              <div className="bg-muted/20 px-6 py-4 border-b border-border">
                <h2 className="font-semibold flex items-center gap-2"><Thermometer className="w-4 h-4 text-primary" /> Current Measurements</h2>
                <p className="text-xs text-muted-foreground mt-1">Patient-reported / Home-measured vitals. Check N/A if unavailable.</p>
              </div>
              <div className="p-6">
                {/* Dense Vitals Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                  {["Temperature", "Heart Rate", "SpO2", "Systolic BP", "Respiratory Rate", "Pain"].map(key => (
                    <div key={key} className="flex items-center gap-3">
                      <Label className="w-1/3 text-xs text-muted-foreground">{key === 'Temperature' ? 'Temperature (°F)' : key}</Label>
                      <Input 
                        type="text" 
                        value={notAvailable[key] ? "" : clinicalForm[key]} 
                        onChange={e => setClinicalForm({...clinicalForm, [key]: e.target.value})} 
                        disabled={notAvailable[key]}
                        className="h-8 text-sm flex-1"
                      />
                      <label className="flex items-center gap-1.5 text-xs text-muted-foreground min-w-[50px]">
                        <input type="checkbox" checked={notAvailable[key] || false} onChange={e => setNotAvailable({...notAvailable, [key]: e.target.checked})} /> N/A
                      </label>
                    </div>
                  ))}
                </div>

                <hr className="my-6 border-border" />

                {/* Current Clinical Context */}
                <h3 className="text-sm font-medium mb-4">Current Clinical Context</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                  {Object.keys(contextFields).map(key => (
                    <div key={key} className="flex items-center gap-3">
                      <Label className="w-1/3 text-xs text-muted-foreground">{key}</Label>
                      <select 
                        value={contextFields[key]} 
                        onChange={e => setContextFields({...contextFields, [key]: e.target.value})}
                        className="h-8 flex-1 rounded-md border border-input bg-background px-2 text-xs shadow-sm"
                      >
                        <option value="">Not Provided</option>
                        {key === "AVPU" ? (
                          <><option value="A">Alert</option><option value="V">Verbal</option><option value="P">Pain</option><option value="U">Unresponsive</option></>
                        ) : (
                          <><option value="Yes">Yes</option><option value="No">No</option></>
                        )}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* ACTIONS AREA */}
            <div className="flex items-center gap-3">
              <Button onClick={evaluateCondition} disabled={loading} size="lg" className="px-8 shadow-sm">
                {loading ? "Evaluating..." : "Evaluate with Safety Gate & ML"}
              </Button>
              <Button variant="outline" size="lg" onClick={() => {
                setSelectedCommonSymptoms([]);
                setSymptomsText("");
                setExtractedFeatures({});
                setClinicalForm({ "Temperature": "", "Heart Rate": "", "SpO2": "", "Systolic BP": "", "Respiratory Rate": "", "Pain": "" });
                setNotAvailable({});
                setContextFields({ "AVPU": "", "Chest Pain": "", "Bleeding": "", "Convulsions": "", "Allergic Reaction": "", "Active High-Risk Condition": "" });
                toast.info("Form reset");
              }}>Clear Form</Button>
            </div>

            {/* PATHWAY & PROVIDER (Shows after evaluation) */}
            {data.step6 && (
              <div className="space-y-8 mt-4 border-t border-border pt-8">
                
                {/* AI Explanation Card */}
                {explanation && (
                  <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-primary/5 px-6 py-4 border-b border-primary/10">
                      <h2 className="font-semibold flex items-center gap-2 text-primary">
                        <Sparkles className="w-4 h-4" /> AI-Generated Explanation
                      </h2>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Explains deterministic 44-feature risk and Safety Gate outcomes for care manager review.</p>
                    </div>
                    <div className="p-6">
                      <div className="text-sm text-foreground leading-relaxed whitespace-pre-line">
                        {explanation}
                      </div>
                    </div>
                  </section>
                )}

                <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                  <div className="bg-muted/20 px-6 py-4 border-b border-border">
                    <h2 className="font-semibold text-primary">Care Pathway</h2>
                  </div>
                  <div className="p-6">
                    <div className="text-xl font-bold text-foreground mb-1">{data.step6.Pathway} - {data.step6.Name}</div>
                    <p className="text-sm text-muted-foreground mb-4">{data.step6.Reason}</p>
                    {data.step5?.status === 'RED' && (
                      <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
                        🚨 IMMEDIATE CLINICAL EVALUATION REQUIRED. DO NOT PROCEED WITH ROUTINE BOOKING.
                      </div>
                    )}
                    {data.step5?.status === 'YELLOW' && (
                      <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-600 text-sm font-medium">
                        ⚠️ URGENT CLINICAL REVIEW RECOMMENDED. PROCEED THROUGH THE APPROPRIATE URGENT-CARE PATHWAY.
                      </div>
                    )}
                  </div>
                </section>

                {data.step7?.Status === "SUCCESS" && data.step7?.Options?.length > 0 && (
                  <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-muted/20 px-6 py-4 border-b border-border">
                      <h2 className="font-semibold text-primary">Provider Matching & Booking</h2>
                    </div>
                    <div className="p-6">
                      {!approved ? (
                        <>
                          <Label className="mb-3 block text-sm font-medium">
                            {data.step5?.status === 'YELLOW' ? 'Recommended Urgent-Care / Clinician Options' : 'Top Matched Providers (Real Quality Scores)'}
                          </Label>
                          <div className="space-y-3 mb-6">
                            {data.step7.Options.map((opt: any, i: number) => (
                              <div key={i} className="border border-border rounded-lg p-3 bg-muted/30 flex justify-between items-center">
                                <div>
                                  <div className="font-medium text-sm">{opt.Name} <span className="text-xs text-muted-foreground ml-1">({opt.Specialty})</span></div>
                                  <div className="text-xs text-muted-foreground">NPI: {opt.NPI || opt.PAC_ID || "Available"} • Quality Score: {opt.Norm_Quality || "90+"}</div>
                                </div>
                                <div className="text-primary font-bold text-sm bg-primary/10 px-2 py-1 rounded">Rank #{i+1}</div>
                              </div>
                            ))}
                          </div>
                          <Label className="mb-2 block text-sm">Care Manager Decision & Audit</Label>
                          <textarea value={auditReason} onChange={e => setAuditReason(e.target.value)} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm mb-4" rows={2} placeholder="Clinical justification for decision..." />
                          <div className="flex gap-2">
                            <Button onClick={() => handleDecision("APPROVE")} className="bg-primary text-primary-foreground">Approve Pathway</Button>
                            <Button onClick={() => handleDecision("REJECT")} variant="destructive">Reject</Button>
                          </div>
                        </>
                      ) : (
                        <div className="bg-muted/30 p-5 rounded-lg border border-border">
                          <h4 className="font-medium mb-4 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-600"/> Book Appointment with Matched Provider</h4>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <select value={apptForm.selectedProviderIndex} onChange={e => setApptForm({...apptForm, selectedProviderIndex: Number(e.target.value)})} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
                              {data.step7.Options.map((opt: any, i: number) => <option key={i} value={i}>{opt.Name}</option>)}
                            </select>
                            <Input type="date" value={apptForm.date} onChange={e => setApptForm({...apptForm, date: e.target.value})} className="h-10 text-sm"/>
                            <Input type="time" value={apptForm.time} onChange={e => setApptForm({...apptForm, time: e.target.value})} className="h-10 text-sm"/>
                          </div>
                          <Button onClick={handleScheduleAppt} className="mt-4 w-full h-10">Confirm & Record Appointment</Button>
                        </div>
                      )}
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Sticky Assessment Summary */}
          <div className="w-full lg:w-80 shrink-0">
            <div className="sticky top-24 bg-card rounded-xl border border-border shadow-sm overflow-hidden flex flex-col">
              <div className="bg-muted px-5 py-4 border-b border-border">
                <h3 className="font-semibold text-sm tracking-wide uppercase text-muted-foreground">Assessment Summary</h3>
              </div>
              
              <div className="p-5 space-y-6">
                <div>
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Step 4 Historical Risk (44 Feats)</div>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-foreground text-lg">{data.step4?.score ?? "—"}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${data.step4?.band === 'HIGH' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>{data.step4?.band ?? "PENDING"}</span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Current Symptoms</div>
                  <ul className="text-sm space-y-1 font-medium">
                    {selectedCommonSymptoms.length === 0 && !symptomsText && <li className="text-muted-foreground font-normal italic">None specified</li>}
                    {selectedCommonSymptoms.map(s => <li key={s}>• {s}</li>)}
                    {symptomsText && <li>• <span className="text-muted-foreground truncate block text-xs font-normal">"{symptomsText}"</span></li>}
                  </ul>
                </div>

                <div>
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">AI Extracted Features</div>
                  {Object.keys(extractedFeatures).length > 0 ? (
                    <ul className="text-xs space-y-1 font-mono text-foreground">
                      {Object.keys(extractedFeatures).map(k => <li key={k}>• {k}</li>)}
                    </ul>
                  ) : (
                    <div className="text-sm text-muted-foreground italic">None detected</div>
                  )}
                </div>
                
                <div>
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Clinical Context</div>
                  <ul className="text-xs space-y-1 text-muted-foreground">
                    <li>Chest Pain: <span className="font-medium text-foreground">{contextFields["Chest Pain"] || "Not Provided"}</span></li>
                    <li>Bleeding: <span className="font-medium text-foreground">{contextFields["Bleeding"] || "Not Provided"}</span></li>
                    <li>AVPU: <span className="font-medium text-foreground">{contextFields["AVPU"] || "Not Provided"}</span></li>
                    <li>Pain: <span className="font-medium text-foreground">{clinicalForm["Pain"] || "Not Provided"}</span></li>
                  </ul>
                </div>

                <div className="pt-4 border-t border-border">
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Safety Status</div>
                  {data.step5?.status === "PENDING" ? (
                    <div className="font-bold text-muted-foreground">PENDING</div>
                  ) : (
                    <div className={`text-xl font-bold ${data.step5?.status === 'RED' ? 'text-destructive' : data.step5?.status === 'YELLOW' ? 'text-amber-500' : 'text-green-600'}`}>
                      {data.step5?.status === 'RED' ? '🔴' : data.step5?.status === 'YELLOW' ? '🟡' : '🟢'} {data.step5?.status}
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-border bg-muted/10 -mx-5 px-5 pb-2">
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Next Action</div>
                  <div className="text-sm font-medium text-primary">
                    {data.step5?.status === 'PENDING' ? "Complete current clinical assessment" :
                     data.step5?.status === 'RED' ? "Emergency care required" :
                     data.step5?.status === 'YELLOW' ? "Review urgent-care / clinician options" :
                     data.step5?.status === 'GREEN' ? "Review provider options" : "Complete assessment"}
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      )}

      <div className="mt-8">
        <SafetyNote text="This assessment combines the 44-feature historical ML model with the deterministic Safety Gate. Emergency care should never be discouraged." />
      </div>
    </AppShell>
  );
}
