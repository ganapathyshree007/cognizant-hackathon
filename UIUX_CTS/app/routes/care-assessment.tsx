import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  CheckCircle2, ShieldAlert, AlertTriangle, UserCheck, 
  Activity, Calendar, Download, Search, Thermometer, HeartPulse, ShieldCheck
} from "lucide-react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "./__root";

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
  const { session } = useAuth();
  
  const paramPatientId = searchParams.patientId;
  const paramEncounterId = searchParams.encounterId;

  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [extractedFeatures, setExtractedFeatures] = useState<Record<string, any>>({});

  // Symptom Inputs
  const [selectedCommonSymptoms, setSelectedCommonSymptoms] = useState<string[]>([]);
  const [symptomsText, setSymptomsText] = useState("");
  const [processingSymptoms, setProcessingSymptoms] = useState(false);

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

  useEffect(() => {
    if (paramPatientId && paramEncounterId && session?.access_token) {
      fetchPatientData(paramPatientId, paramEncounterId, false);
    }
  }, [paramPatientId, paramEncounterId, session]);

  const fetchPatientData = async (pid: string, eid: string, isStage2 = false, contextOverride = null) => {
    if (!session?.access_token) return;
    setLoading(true); setError(null);
    if (!isStage2) { setData(null); setExplanation(null); setApproved(false); setSymptomsText(""); setSelectedCommonSymptoms([]); }
    
    let contextToSend: any = {};
    if (isStage2) {
      contextToSend = contextOverride || buildFinalContext();
    }
    
    try {
      const response = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session.access_token}` },
        body: JSON.stringify({ patient_id: pid, encounter_id: eid, clinical_context: contextToSend })
      });
      const result = await response.json();
      if (result.error) setError(result);
      else {
        setData(result);
        if (isStage2 && result.step5?.status !== "PENDING") fetchExplanation(result, contextToSend);
      }
    } catch (e: any) { setError({ message: e.message, error: "CONNECTION_ERROR" }); }
    setLoading(false);
  };

  const fetchExplanation = async (resultData: any, contextToSend: any) => {
    try {
      const response = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session?.access_token}` },
        body: JSON.stringify({
          step4: resultData.step4 || {}, step5: resultData.step5 || {},
          step6: resultData.step6 || {}, step7: resultData.step7 || {},
          clinical_context: contextToSend 
        })
      });
      const expRes = await response.json();
      setExplanation(expRes.explanation);
    } catch (e) { console.error(e); }
  };

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

  const extractSymptoms = async () => {
    if (!symptomsText.trim()) return;
    setProcessingSymptoms(true);
    try {
      const response = await fetch('/api/symptoms/llm-extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session?.access_token}` },
        body: JSON.stringify({ symptoms: symptomsText })
      });
      const result = await response.json();
      if (result.status === "success") setExtractedFeatures(result.extracted_features);
    } catch (e) { alert("Error extracting symptoms."); }
    setProcessingSymptoms(false);
  };

  const evaluateCondition = async () => {
    if (symptomsText.trim() && Object.keys(extractedFeatures).length === 0) {
      await extractSymptoms();
    }
    const finalContext = buildFinalContext();
    await fetchPatientData(paramPatientId!, paramEncounterId!, true, finalContext);
  };

  const handleDecision = async (action: string) => {
    if ((action === "REJECT" || action === "ESCALATE") && !auditReason) return alert(`A reason is required to ${action}.`);
    try {
      const response = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session?.access_token}` },
        body: JSON.stringify({
          patient_id: paramPatientId, encounter_id: paramEncounterId, action: action, reason: auditReason || "Approved",
          system_pathway: data?.step6?.Pathway || "N/A", system_provider: data?.step7?.Options?.[0]?.Name || "NONE",
          selected_provider: data?.step7?.Options?.[0]?.Name || "NONE"
        })
      });
      if (response.ok) { setAuditReason(""); if (action === "APPROVE") setApproved(true); }
    } catch (e) { alert("Error saving audit trail."); }
  };

  const handleScheduleAppt = async () => {
    if (!apptForm.date || !apptForm.time) return alert("Select date and time.");
    const provider = data.step7.Options[apptForm.selectedProviderIndex];
    try {
      const response = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session?.access_token}` },
        body: JSON.stringify({
          patient_id: paramPatientId, encounter_id: paramEncounterId, provider_name: provider.Name, provider_npi: String(provider.NPI || "N/A"), pac_id: String(provider.PAC_ID || "N/A"),
          provider_specialty: provider.Specialty, appointment_date: apptForm.date, appointment_time: apptForm.time
        })
      });
      if (response.ok) { alert("Appointment created successfully! It will now appear in Follow-ups."); navigate({ to: "/follow-ups" }); }
    } catch (e) { alert("Failed to schedule appointment."); }
  };

  const currentStepIndex = approved ? 6 : data?.step7?.Status === "SUCCESS" ? 5 : data?.step6 ? 4 : data?.step5?.status && data.step5.status !== "PENDING" ? 3 : data?.step4 ? 1 : 0;

  if (!paramPatientId || !paramEncounterId) {
    return (
      <AppShell>
        <div className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight">Care Assessment</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Select a patient to begin the clinical orchestration workflow.</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-8 max-w-lg shadow-sm">
          <h2 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2"><UserCheck className="w-5 h-5 text-primary" /> Find Patient</h2>
          <form className="flex gap-3" onSubmit={(e) => { e.preventDefault(); if (searchInput) navigate({ to: "/patients", search: { q: searchInput } as any }); }}>
            <Input placeholder="Enter Patient ID..." value={searchInput} onChange={e => setSearchInput(e.target.value)} className="flex-1" />
            <Button type="button" onClick={() => navigate({ to: "/patients" })}>Search</Button>
          </form>
        </div>
      </AppShell>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <header className="border-b border-border bg-card sticky top-0 z-10">
        <div className="mx-auto w-[95%] px-4 py-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Link to="/patients" className="text-muted-foreground hover:text-foreground">Patients</Link>
              <span className="text-muted-foreground">/</span> Assessment
            </h1>
            <p className="text-xs text-muted-foreground mt-1">Patient: {paramPatientId} • Encounter: {paramEncounterId}</p>
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
      </header>

      <main className="mx-auto w-[95%] px-4 py-8">
        {error && <div className="mb-6 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"><AlertTriangle className="size-5 shrink-0" /><span>{error.message}</span></div>}
        
        {loading && !data && <div className="p-12 text-center text-muted-foreground animate-pulse">Loading historical context...</div>}

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
                      <option value="Fever">Fever</option>
                      <option value="Cough">Cough</option>
                      <option value="Chest pain">Chest pain</option>
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
                      placeholder="Describe what the patient is experiencing naturally..."
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm min-h-[100px]"
                    />
                    <div className="flex justify-end mt-2">
                      <Button variant="secondary" size="sm" onClick={extractSymptoms} disabled={processingSymptoms || !symptomsText.trim()}>
                        {processingSymptoms ? "Extracting..." : "Extract Features"}
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
                        <Label className="w-1/3 text-xs text-muted-foreground">{key}</Label>
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
                <Button variant="outline" size="lg">Clear Form</Button>
              </div>

              {/* PATHWAY & PROVIDER (Shows after evaluation) */}
              {data.step6 && (
                <div className="space-y-8 mt-12 border-t border-border pt-12">
                  <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                    <div className="bg-muted/20 px-6 py-4 border-b border-border">
                      <h2 className="font-semibold text-primary">Care Pathway (Step 6)</h2>
                    </div>
                    <div className="p-6">
                      <div className="text-xl font-bold text-foreground mb-1">{data.step6.Pathway} - {data.step6.Name}</div>
                      <p className="text-sm text-muted-foreground mb-4">{data.step6.Reason}</p>
                      {(data.step5.status === 'RED' || data.step5.status === 'YELLOW') && (
                        <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
                          🚨 IMMEDIATE CLINICAL EVALUATION REQUIRED. DO NOT PROCEED WITH ROUTINE BOOKING.
                        </div>
                      )}
                    </div>
                  </section>

                  {data.step7?.Status === "SUCCESS" && (
                    <section className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
                      <div className="bg-muted/20 px-6 py-4 border-b border-border">
                        <h2 className="font-semibold text-primary">Provider & Appointment (Step 7)</h2>
                      </div>
                      <div className="p-6">
                        {!approved ? (
                          <>
                            <Label className="mb-3 block text-sm font-medium">Top Recommended Providers</Label>
                            <div className="space-y-3 mb-6">
                              {data.step7.Options.map((opt: any, i: number) => (
                                <div key={i} className="border border-border rounded-lg p-3 bg-muted/30 flex justify-between items-center">
                                  <div>
                                    <div className="font-medium text-sm">{opt.Name} <span className="text-xs text-muted-foreground ml-1">({opt.Specialty})</span></div>
                                  </div>
                                  <div className="text-primary font-bold text-sm bg-primary/10 px-2 py-1 rounded">Rank #{i+1}</div>
                                </div>
                              ))}
                            </div>
                            <Label className="mb-2 block text-sm">Care Manager Decision & Audit</Label>
                            <textarea value={auditReason} onChange={e => setAuditReason(e.target.value)} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm mb-4" rows={2} placeholder="Justification for decision..." />
                            <div className="flex gap-2">
                              <Button onClick={() => handleDecision("APPROVE")} className="bg-primary text-primary-foreground">Approve</Button>
                              <Button onClick={() => handleDecision("REJECT")} variant="destructive">Reject</Button>
                            </div>
                          </>
                        ) : (
                          <div className="bg-muted/30 p-5 rounded-lg border border-border">
                            <h4 className="font-medium mb-4 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-600"/> Book Appointment</h4>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                              <select value={apptForm.selectedProviderIndex} onChange={e => setApptForm({...apptForm, selectedProviderIndex: Number(e.target.value)})} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
                                {data.step7.Options.map((opt: any, i: number) => <option key={i} value={i}>{opt.Name}</option>)}
                              </select>
                              <Input type="date" value={apptForm.date} onChange={e => setApptForm({...apptForm, date: e.target.value})} className="h-10 text-sm"/>
                              <Input type="time" value={apptForm.time} onChange={e => setApptForm({...apptForm, time: e.target.value})} className="h-10 text-sm"/>
                            </div>
                            <Button onClick={handleScheduleAppt} className="mt-4 w-full h-10">Confirm Booking</Button>
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
                      {approved ? "Book appointment" : data.step7 ? "Review provider options" : data.step6 ? "Review pathway" : "Complete assessment"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
