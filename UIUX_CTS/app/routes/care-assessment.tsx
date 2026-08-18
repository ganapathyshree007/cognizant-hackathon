import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  CheckCircle2, ShieldAlert, AlertTriangle, UserCheck, 
  Activity, Calendar, Download, Search, Thermometer, HeartPulse, ShieldCheck, Sparkles, ArrowLeft
} from "lucide-react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { getPatientName } from "@/lib/utils";

type SearchParams = { patientId?: string; encounterId?: string; };

export const Route = createFileRoute("/care-assessment")({
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    patientId: typeof search.patientId === "string" ? search.patientId : undefined,
    encounterId: typeof search.encounterId === "string" ? search.encounterId : undefined,
  }),
  head: () => ({ meta: [{ title: "Care Assessment — CarePath" }] }),
  component: CareAssessmentPage,
});

const PROGRESS_STEPS = ["Patient Context", "Symptoms", "Measurements", "Safety", "Pathway", "Provider", "Appointment"];

function CareAssessmentPage() {
  const navigate = useNavigate();
  const searchParams = Route.useSearch();
  
  const paramPatientId = searchParams.patientId;
  const paramEncounterId = searchParams.encounterId;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [patientName, setPatientName] = useState("");

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

  // Auto-load patient name and initial risk assessment when parameters exist
  useEffect(() => {
    async function loadInitialData() {
      if (paramPatientId && paramEncounterId) {
        setLoading(true);
        setError(null);
        try {
          // Get patient gender via backend API (service key bypasses RLS)
          const pRes = await fetch(`/api/patients/${paramPatientId}`);
          let gender = "F";
          if (pRes.ok) {
            const pData = await pRes.json();
            gender = pData?.gender || "F";
          }
          const name = getPatientName(paramPatientId, gender);
          setPatientName(name);

          // Initial Stage 1 evaluate call (empty clinical_context)
          const res = await fetch("/api/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              patient_id: paramPatientId,
              encounter_id: paramEncounterId,
              clinical_context: {}
            })
          });
          if (res.ok) {
            setData(await res.json());
          } else {
            const errJson = await res.json();
            setError(errJson);
          }
        } catch (e: any) {
          console.error("Error loading initial data:", e);
          setError({ message: e.message || "Failed to load patient historical risk." });
        } finally {
          setLoading(false);
        }
      }
    }
    loadInitialData();
  }, [paramPatientId, paramEncounterId]);

  const extractSymptoms = async () => {
    if (!symptomsText.trim()) return;
    setProcessingSymptoms(true);
    try {
      const res = await fetch("/api/symptoms/llm-extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms: symptomsText })
      });
      if (res.ok) {
        const resJson = await res.json();
        if (resJson.extracted_features) {
          setExtractedFeatures(resJson.extracted_features);
          
          // Map extracted features to vitals/clinical form
          const newVitals = { ...clinicalForm };
          const newContext = { ...contextFields };
          
          Object.keys(resJson.extracted_features).forEach(key => {
            const val = resJson.extracted_features[key];
            if (key in clinicalForm) {
              newVitals[key] = String(val);
            } else if (key in contextFields) {
              newContext[key] = val === true || val === "Yes" ? "Yes" : "No";
            }
          });
          
          setClinicalForm(newVitals);
          setContextFields(newContext);
          toast.success("Symptoms extracted successfully!");
        }
      } else {
        toast.error("Failed to extract symptoms");
      }
    } catch (e) {
      toast.error("Network error during symptom extraction");
    } finally {
      setProcessingSymptoms(false);
    }
  };

  const evaluateCondition = async () => {
    setLoading(true);
    setError(null);
    try {
      const contextToSend: any = {};
      
      // Map vitals
      Object.keys(clinicalForm).forEach(key => {
        if (clinicalForm[key] !== "" && !notAvailable[key]) {
          const val = clinicalForm[key];
          if (!isNaN(Number(val))) {
            contextToSend[key] = Number(val);
          } else {
            contextToSend[key] = val;
          }
        }
      });

      // Map context select fields
      Object.keys(contextFields).forEach(key => {
        if (contextFields[key] !== "") {
          contextToSend[key] = contextFields[key] === "Yes" ? true : contextFields[key] === "No" ? false : contextFields[key];
        }
      });

      // Include common symptoms in text representation if selected
      if (selectedCommonSymptoms.length > 0) {
        contextToSend["symptoms_summary"] = selectedCommonSymptoms.join(", ");
      }

      // 1. Post to evaluate
      const response = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: paramPatientId,
          encounter_id: paramEncounterId || "UNKNOWN",
          clinical_context: contextToSend
        })
      });

      if (!response.ok) {
        const errJson = await response.json();
        setError(errJson);
        toast.error("Clinical evaluation failed");
        setLoading(false);
        return;
      }

      const result = await response.json();
      setData(result);

      // 2. Fetch explanation from explain if not pending
      if (result.step5?.status !== "PENDING") {
        const expRes = await fetch("/api/explain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            step4: result.step4 || {},
            step5: result.step5 || {},
            step6: result.step6 || {},
            step7: result.step7 || {},
            clinical_context: contextToSend
          })
        });
        if (expRes.ok) {
          const expJson = await expRes.json();
          setExplanation(expJson.explanation);
        }
      }

      toast.success("Clinical evaluation complete");
    } catch (e: any) {
      console.error(e);
      setError({ message: e.message || "Network connection error evaluating patient." });
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (action: string) => {
    if ((action === "REJECT" || action === "ESCALATE") && !auditReason) {
      toast.error(`A reason is required to ${action.toLowerCase()}.`);
      return;
    }

    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: paramPatientId,
          encounter_id: paramEncounterId || "UNKNOWN",
          action: action,
          reason: auditReason || "Approved pathway recommendation",
          system_pathway: data.step6?.Pathway || "P3",
          system_provider: data.step7?.Options?.[0]?.Name || "None",
          selected_provider: data.step7?.Options?.[apptForm.selectedProviderIndex]?.Name || "None"
        })
      });

      if (res.ok) {
        if (action === "APPROVE") {
          setApproved(true);
          toast.success("Recommendation approved — audit trail recorded");
        } else {
          toast.info(`Decision "${action}" recorded with rationale.`);
        }
        setAuditReason("");
      } else {
        toast.error("Failed to record decision");
      }
    } catch (err) {
      toast.error("Network error recording decision");
    }
  };

  const handleScheduleAppt = async () => {
    if (!apptForm.date || !apptForm.time) {
      toast.error("Please select date and time.");
      return;
    }
    const provider = data.step7.Options[apptForm.selectedProviderIndex];
    try {
      const res = await fetch("/api/appointments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: paramPatientId,
          encounter_id: paramEncounterId || "UNKNOWN",
          provider_name: provider.Name,
          provider_npi: provider.NPI || "",
          pac_id: provider.PAC_ID || "",
          provider_specialty: provider.Specialty || "",
          appointment_date: apptForm.date,
          appointment_time: apptForm.time
        })
      });

      if (res.ok) {
        toast.success(`Appointment scheduled with ${provider.Name} on ${apptForm.date} at ${apptForm.time}`);
        setTimeout(() => navigate({ to: `/patients/${paramPatientId}`, search: { encounterId: paramEncounterId } }), 1500);
      } else {
        toast.error("Failed to schedule appointment");
      }
    } catch (err) {
      toast.error("Network error scheduling appointment");
    }
  };

  const currentStepIndex = approved ? 6 : data?.step7?.Status === "SUCCESS" ? 5 : data?.step6 ? 4 : data?.step5?.status && data.step5.status !== "PENDING" ? 3 : data?.step4 ? 1 : 0;

  if (!paramPatientId || !paramEncounterId) {
    return (
      <AppShell>
        <Breadcrumbs items={[
          { label: "Dashboard", to: "/" },
          { label: "Care Assessment" },
        ]} />
        <div className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight">Care Assessment</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Select a patient to begin the clinical orchestration workflow.</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-8 max-w-lg shadow-sm">
          <h2 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2"><UserCheck className="w-5 h-5 text-primary" /> Find Patient</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Search for a patient from the Patients list to begin an assessment.
          </p>
          <Button onClick={() => navigate({ to: "/patients" })}>Go to Patient List</Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients", to: "/patients" },
        { label: patientName || `Patient ${paramPatientId?.substring(0, 8)}`, to: `/patients/${paramPatientId}`, search: { encounterId: paramEncounterId } },
        { label: "Care Assessment" },
      ]} />

      {/* Sticky Progress Header */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-4 mb-8 sticky top-0 z-10">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div>
            <h1 className="text-lg font-semibold">Care Assessment for {patientName || "Patient"}</h1>
            <p className="text-xs text-muted-foreground mt-0.5">Patient: {paramPatientId} · Encounter: {paramEncounterId}</p>
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

      {error && <div className="mb-6 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"><AlertTriangle className="size-5 shrink-0" /><span>{error.message}</span></div>}
      
      {loading && !data && <div className="p-12 text-center text-muted-foreground animate-pulse">Loading patient historical context...</div>}

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
                  <Label className="mb-2 block text-sm">Describe Symptoms</Label>
                  <textarea 
                    value={symptomsText}
                    onChange={(e) => setSymptomsText(e.target.value)}
                    placeholder="Describe naturally what the patient is experiencing... Click 'Extract' to auto-populate the measurements below."
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm min-h-[100px]"
                  />
                  <div className="flex justify-end mt-2">
                    <Button variant="secondary" size="sm" onClick={extractSymptoms} disabled={processingSymptoms || !symptomsText.trim()}>
                      {processingSymptoms ? "Extracting..." : "Extract Vital Features"}
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
                <p className="text-xs text-muted-foreground mt-1">Patient-reported / Home-measured data. Check N/A if unavailable.</p>
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
                {loading ? "Evaluating..." : "Evaluate Current Condition"}
              </Button>
              <Button variant="outline" size="lg" onClick={() => {
                setSelectedCommonSymptoms([]);
                setSymptomsText("");
                setExtractedFeatures({});
                setClinicalForm({ "Temperature": "", "Heart Rate": "", "SpO2": "", "Systolic BP": "", "Respiratory Rate": "", "Pain": "" });
                setNotAvailable({});
                setContextFields({ "AVPU": "", "Chest Pain": "", "Bleeding": "", "Convulsions": "", "Allergic Reaction": "", "Active High-Risk Condition": "" });
                setExplanation(null);
                toast.info("Form cleared");
              }}>Clear Form</Button>
            </div>

            {/* PATHWAY & PROVIDER (Shows after evaluation) */}
            {data.step6 && (
              <div className="space-y-8 mt-4 border-t border-border pt-8 animate-in fade-in duration-300">
                
                {/* AI Explanation Card */}
                {explanation && (
                  <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-primary/5 px-6 py-4 border-b border-primary/10">
                      <h2 className="font-semibold flex items-center gap-2 text-primary">
                        <Sparkles className="w-4 h-4" /> AI-Generated Explanation
                      </h2>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Generated by the reasoning layer for care manager review. Not shown to the member.</p>
                    </div>
                    <div className="p-6">
                      <div className="text-sm text-foreground leading-relaxed whitespace-pre-line">
                        {explanation.split('\n').map((line, i) => {
                          if (line.startsWith('**') && line.endsWith('**')) {
                            return <p key={i} className="font-semibold mt-3 mb-1">{line.replace(/\*\*/g, '')}</p>;
                          }
                          if (line.startsWith('- ')) {
                            return <p key={i} className="ml-4 text-muted-foreground">• {line.substring(2)}</p>;
                          }
                          if (line.startsWith('*') && line.endsWith('*')) {
                            return <p key={i} className="text-xs text-muted-foreground italic mt-3 border-t border-border pt-3">{line.replace(/\*/g, '')}</p>;
                          }
                          return line ? <p key={i} className="text-muted-foreground">{line}</p> : <br key={i} />;
                        })}
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
                    {data.step5.status === 'RED' && (
                      <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
                        🚨 IMMEDIATE CLINICAL EVALUATION REQUIRED. DO NOT PROCEED WITH ROUTINE BOOKING.
                      </div>
                    )}
                    {data.step5.status === 'YELLOW' && (
                      <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-600 text-sm font-medium">
                        ⚠️ URGENT CLINICAL REVIEW RECOMMENDED. PROCEED THROUGH THE APPROPRIATE URGENT-CARE PATHWAY.
                      </div>
                    )}
                  </div>
                </section>

                {data.step7?.Status === "SUCCESS" && (
                  <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-muted/20 px-6 py-4 border-b border-border">
                      <h2 className="font-semibold text-primary">Provider & Appointment</h2>
                    </div>
                    <div className="p-6">
                      {!approved ? (
                        <>
                          <Label className="mb-3 block text-sm font-medium">
                            {data.step5.status === 'YELLOW' ? 'Recommended Urgent-Care / Clinician Options' : 'Top Recommended Providers'}
                          </Label>
                          <div className="space-y-3 mb-6">
                            {data.step7.Options.map((opt: any, i: number) => (
                              <div key={i} className="border border-border rounded-lg p-3 bg-muted/30 flex justify-between items-center">
                                <div>
                                  <div className="font-medium text-sm">{opt.Name} <span className="text-xs text-muted-foreground ml-1">({opt.Specialty})</span></div>
                                  <div className="text-xs text-muted-foreground mt-0.5">NPI: {opt.NPI} · Quality Score: {Math.round(opt.Norm_Quality || 50)}</div>
                                </div>
                                <div className="text-primary font-bold text-sm bg-primary/10 px-2 py-1 rounded">Rank #{i+1}</div>
                              </div>
                            ))}
                          </div>
                          <Label className="mb-2 block text-sm">Care Manager Decision & Audit Comment</Label>
                          <textarea value={auditReason} onChange={e => setAuditReason(e.target.value)} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm mb-4" rows={2} placeholder=" rational justification for selecting or overriding the recommended pathway..." />
                          <div className="flex gap-2">
                            <Button onClick={() => handleDecision("APPROVE")} className="bg-primary text-primary-foreground">Approve Pathway</Button>
                            <Button onClick={() => handleDecision("REJECT")} variant="destructive">Reject / Re-evaluate</Button>
                          </div>
                        </>
                      ) : (
                        <div className="bg-muted/30 p-5 rounded-lg border border-border animate-in slide-in-from-bottom duration-300">
                          <h4 className="font-medium mb-4 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-600"/> Book Appointment</h4>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <select value={apptForm.selectedProviderIndex} onChange={e => setApptForm({...apptForm, selectedProviderIndex: Number(e.target.value)})} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
                              {data.step7.Options.map((opt: any, i: number) => <option key={i} value={i}>{opt.Name}</option>)}
                            </select>
                            <Input type="date" value={apptForm.date} onChange={e => setApptForm({...apptForm, date: e.target.value})} className="h-10 text-sm"/>
                            <Input type="time" value={apptForm.time} onChange={e => setApptForm({...apptForm, time: e.target.value})} className="h-10 text-sm"/>
                          </div>
                          <Button onClick={handleScheduleAppt} className="mt-4 w-full h-10">Confirm & Record Booking</Button>
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
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Historical Risk</div>
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-foreground text-lg">{data.step4.score}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${data.step4.band === 'HIGH' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>{data.step4.band}</span>
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
                  <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">AI Detected Features</div>
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
                    <div className={`text-xl font-bold ${data.step5.status === 'RED' ? 'text-destructive' : data.step5.status === 'YELLOW' ? 'text-amber-500' : 'text-green-600'}`}>
                      {data.step5.status === 'RED' ? '🔴' : data.step5.status === 'YELLOW' ? '🟡' : '🟢'} {data.step5.status}
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
        <SafetyNote text="This assessment supports care navigation and does not replace clinical judgment. If the member is experiencing a medical emergency, emergency care should never be discouraged." />
      </div>
    </AppShell>
  );
}
