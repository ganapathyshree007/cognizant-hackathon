import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Play, Calendar, HeartPulse, Activity, ChevronRight } from "lucide-react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { getPatientName } from "@/lib/utils";

export const Route = createFileRoute("/patients/$patientId")({
  validateSearch: (search: Record<string, unknown>) => ({
    encounterId: typeof search.encounterId === "string" ? search.encounterId : undefined,
  }),
  head: () => ({ meta: [{ title: "Patient Profile — CarePath" }] }),
  component: PatientProfile,
});

function PatientProfile() {
  const { patientId } = Route.useParams();
  const { encounterId = "UNKNOWN" } = Route.useSearch();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [patientInfo, setPatientInfo] = useState<any>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any>({
    score: 0,
    band: "MEDIUM",
    drivers: ["No historical risk drivers found."]
  });
  const [safetyStatus, setSafetyStatus] = useState("GREEN");
  const [pathway, setPathway] = useState("Routine Outpatient Follow-up");

  // Outcome Modal State
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [outcomeAppt, setOutcomeAppt] = useState<any>(null);
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [outcomeFollowUp, setOutcomeFollowUp] = useState(true);

  const fetchProfileAndData = async () => {
    setLoading(true);
    try {
      const pRes = await fetch(`/api/patients/${patientId}`);
      let pData = null;
      if (pRes.ok) {
        pData = await pRes.json();
      }
      
      let age = 45;
      let gender = "F";
      if (pData) {
        age = Math.round(pData.age_at_index || 45);
        gender = pData.gender || "F";
      }

      const name = getPatientName(patientId, gender);
      setPatientInfo({
        name,
        age,
        dob: `${gender === "M" ? "Male" : "Female"} · DOB Not on file`,
        phone: "Not available on file",
        email: `${name.toLowerCase().replace(" ", ".")}@hospital.org`
      });

      // 2. Fetch risk data from backend /api/evaluate
      const evalRes = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          encounter_id: encounterId || "UNKNOWN",
          clinical_context: {}
        })
      });

      if (evalRes.ok) {
        const resJson = await evalRes.json();
        if (resJson.step4) {
          setRiskData({
            score: resJson.step4.score || 0,
            band: resJson.step4.band || "MEDIUM",
            drivers: resJson.step4.drivers || ["No historical drivers found."]
          });
        }
        if (resJson.step5) {
          setSafetyStatus(resJson.step5.status || "GREEN");
        }
        if (resJson.step6) {
          setPathway(resJson.step6.Name || "Routine Outpatient Follow-up");
        }
      }

      // 3. Fetch appointments
      const apptRes = await fetch(`/api/appointments/${patientId}`);
      if (apptRes.ok) {
        setAppointments(await apptRes.json());
      }

      // 4. Fetch outcomes
      const outcomeRes = await fetch(`/api/outcomes/${patientId}`);
      if (outcomeRes.ok) {
        setOutcomes(await outcomeRes.json());
      }

    } catch (e) {
      console.error("Error loading patient profile data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileAndData();
  }, [patientId, encounterId]);

  const handleStatusUpdate = async (appt: any, newStatus: string) => {
    if (newStatus === "Completed") {
      setOutcomeAppt(appt);
      setOutcomeNotes("");
      setOutcomeFollowUp(true);
      setOutcomeModalOpen(true);
      return;
    }
    
    try {
      const res = await fetch(`/api/appointments/${appt.appointment_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        toast.success(`Appointment marked as ${newStatus}`);
        fetchProfileAndData();
      } else {
        toast.error("Failed to update appointment status");
      }
    } catch (err) {
      toast.error("Network error updating appointment status");
    }
  };

  const saveOutcome = async () => {
    if (!outcomeNotes.trim()) {
      toast.error("Please enter clinical notes.");
      return;
    }

    try {
      // 1. Update appointment status to Completed
      const resAppt = await fetch(`/api/appointments/${outcomeAppt.appointment_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "Completed" })
      });

      if (!resAppt.ok) {
        toast.error("Failed to mark appointment completed");
        return;
      }

      // 2. Post outcome
      const resOutcome = await fetch("/api/outcomes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          appointment_id: outcomeAppt.appointment_id,
          patient_id: patientId,
          encounter_id: encounterId || "UNKNOWN",
          clinical_notes: outcomeNotes,
          follow_up_required: outcomeFollowUp
        })
      });

      if (resOutcome.ok) {
        toast.success("Outcome saved successfully");
        setOutcomeModalOpen(false);
        fetchProfileAndData();
      } else {
        toast.error("Failed to save outcome");
      }
    } catch (err) {
      toast.error("Network error saving outcome");
    }
  };

  if (loading || !patientInfo) {
    return (
      <AppShell>
        <div className="flex h-[50vh] flex-col items-center justify-center text-muted-foreground animate-pulse">
          Loading patient profile and database records...
        </div>
      </AppShell>
    );
  }

  // Find latest visit from outcomes
  const latestOutcome = outcomes.length > 0 ? outcomes[0] : null;

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients", to: "/patients" },
        { label: patientInfo.name },
      ]} />

      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{patientInfo.name}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">ID: {patientId} · Encounter: {encounterId}</p>
        </div>
        <Button onClick={() => navigate({ to: "/care-assessment", search: { patientId, encounterId } })} size="lg" className="gap-2">
          Start Care Assessment <Play className="w-4 h-4" />
        </Button>
      </div>

      {/* Overview & Care Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2">Patient Overview</h2>
          <div className="grid grid-cols-2 gap-y-4 text-sm">
            <div><span className="text-muted-foreground block">Age</span><span className="font-medium">{patientInfo.age}</span></div>
            <div><span className="text-muted-foreground block">Gender/Info</span><span className="font-medium">{patientInfo.dob}</span></div>
            <div><span className="text-muted-foreground block">Phone</span><span className="font-medium">{patientInfo.phone}</span></div>
            <div><span className="text-muted-foreground block">Email</span><span className="font-medium">{patientInfo.email}</span></div>
          </div>
        </div>
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2">Current Care Status</h2>
          <div className="grid grid-cols-2 gap-y-4 text-sm">
            <div><span className="text-muted-foreground block">Current Risk</span>
              <span className={`font-medium ${riskData.band === 'HIGH' ? 'text-destructive' : 'text-primary'}`}>{riskData.band}</span>
            </div>
            <div><span className="text-muted-foreground block">Safety Status</span>
              <span className={`font-medium ${safetyStatus === 'RED' ? 'text-destructive' : safetyStatus === 'YELLOW' ? 'text-amber-600' : 'text-green-600'}`}>{safetyStatus}</span>
            </div>
            <div className="col-span-2"><span className="text-muted-foreground block">Care Pathway</span>
              <span className="font-medium">{pathway}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        {/* Latest Visit Card */}
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2 flex items-center gap-2">
            <HeartPulse className="w-4 h-4" /> Latest Outcome / Visit
          </h2>
          {latestOutcome ? (
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex-1">
                <div className="text-sm font-medium mb-1">{new Date(latestOutcome.timestamp).toLocaleDateString()}</div>
                <div className="text-lg font-bold text-foreground">Encounter: {latestOutcome.encounter_id}</div>
                <div className="text-xs text-muted-foreground">Recorded outcome</div>
              </div>
              <div className="flex-1 space-y-3">
                <div className="text-sm"><span className="text-muted-foreground mr-2">Status:</span><span className="font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded text-xs">Completed</span></div>
                <div className="text-sm"><span className="text-muted-foreground mr-2">Follow-up:</span><span className="font-medium">{latestOutcome.follow_up_required ? "Required" : "Not Required"}</span></div>
                <div className="text-sm bg-muted/30 p-3 rounded-lg border border-border">
                  <span className="text-muted-foreground block mb-1 text-xs uppercase tracking-wider">Outcome Summary</span>
                  <span className="font-medium">{latestOutcome.clinical_notes}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-6 text-sm">No completed outcomes recorded in database.</div>
          )}
        </div>

        {/* Historical Risk */}
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2">
            Historical Risk
          </h2>
          <div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-3xl font-bold tracking-tight text-foreground">{riskData.score}</span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${riskData.band === 'HIGH' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>{riskData.band}</span>
            </div>
            <ul className="mt-4 text-xs text-muted-foreground list-disc pl-4 space-y-1">
              {riskData.drivers.map((d: string, i: number) => <li key={i}>{d}</li>)}
            </ul>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        
        {/* Chronological Timeline */}
        <div className="lg:col-span-1">
          <h2 className="text-lg font-medium text-foreground mb-4">Patient History</h2>
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm max-h-[400px] overflow-y-auto">
            <div className="relative border-l-2 border-border ml-3 space-y-6 pb-4">
              
              {appointments.map((appt, i) => (
                <div key={i} className="relative pl-6">
                  <div className={`absolute -left-1.5 w-3 h-3 rounded-full border-2 border-background ${
                    appt.status === 'Completed' ? 'bg-green-500' : 
                    appt.status === 'No-Show' || appt.status === 'Cancelled' ? 'bg-destructive' : 
                    'bg-primary'
                  }`}></div>
                  <div className="text-xs text-muted-foreground font-medium mb-1">{appt.appointment_date}</div>
                  <div className="bg-muted/20 border border-border p-3 rounded-lg text-sm">
                    <div className="font-semibold">{appt.status === 'Completed' ? 'Completed Visit' : appt.status === 'Scheduled' ? 'Upcoming Appointment' : appt.status}</div>
                    <div className="text-muted-foreground mt-1 text-xs">Provider: {appt.provider_name}</div>
                    {appt.status === 'Completed' && <div className="mt-2 text-xs text-green-700 bg-green-50 p-1.5 rounded border border-green-100">Outcome recorded</div>}
                  </div>
                </div>
              ))}

              <div className="relative pl-6 opacity-70">
                <div className="absolute -left-1.5 w-3 h-3 rounded-full border-2 border-background bg-blue-400"></div>
                <div className="text-xs text-muted-foreground font-medium mb-1">Index Date</div>
                <div className="bg-muted/20 border border-border p-3 rounded-lg text-sm">
                  <div className="font-semibold">Care Assessment</div>
                  <div className="text-muted-foreground mt-1 text-xs">Initial Risk: {riskData.band}</div>
                </div>
              </div>
              
            </div>
          </div>
        </div>

        {/* Actionable Appointments List */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-medium text-foreground mb-4 flex items-center justify-between">
            <span>Manage Appointments</span>
            <Link to="/patients" className="text-sm font-normal text-primary hover:underline">View All Patients</Link>
          </h2>
          
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/20">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-5 py-3">Date/Time</th>
                  <th className="px-5 py-3">Provider</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Update</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {appointments.map(a => (
                  <tr key={a.appointment_id} className="hover:bg-muted/40 transition-colors">
                    <td className="px-5 py-4 whitespace-nowrap text-foreground">{a.appointment_date} <span className="text-muted-foreground text-xs block">{a.appointment_time}</span></td>
                    <td className="px-5 py-4 whitespace-nowrap text-foreground">{a.provider_name} <span className="text-xs text-muted-foreground block">{a.provider_specialty}</span></td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        a.status === 'Completed' ? 'bg-green-100 text-green-800' : 
                        a.status === 'Rescheduled' ? 'bg-purple-100 text-purple-800' :
                        (a.status === 'Cancelled' || a.status === 'No-Show' ? 'bg-destructive/10 text-destructive' : 'bg-blue-100 text-blue-800')
                      }`}>{a.status}</span>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      {a.status !== 'Completed' && a.status !== 'Cancelled' && (
                         <select 
                         onChange={(e) => handleStatusUpdate(a, e.target.value)}
                         value={a.status}
                         className="h-8 rounded-md border border-input bg-background px-2 text-xs shadow-sm"
                       >
                         <option value={a.status}>{a.status}</option>
                         <option value="Completed">Mark Completed</option>
                         <option value="No-Show">Mark No-Show</option>
                         <option value="Cancelled">Cancel</option>
                       </select>
                      )}
                    </td>
                  </tr>
                ))}
                {appointments.length === 0 && <tr><td colSpan={4} className="px-5 py-8 text-center text-muted-foreground">No appointments found in database.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Outcome Modal */}
      {outcomeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-green-600" /> Enter Consultation Outcome</h3>
            <p className="text-sm text-muted-foreground mb-4">You are marking the appointment with {outcomeAppt?.provider_name} as Completed.</p>
            <div className="space-y-4 mb-6">
              <div>
                <label className="text-xs font-medium mb-1 block">Clinical Notes / Outcome</label>
                <textarea 
                  rows={4} 
                  placeholder="Summarize the diagnosis, treatment, and outcome..." 
                  value={outcomeNotes} 
                  onChange={e => setOutcomeNotes(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="followUpCheck" 
                  checked={outcomeFollowUp} 
                  onChange={e => setOutcomeFollowUp(e.target.checked)}
                  className="rounded border-input text-primary" 
                />
                <label htmlFor="followUpCheck" className="text-sm font-medium">Follow-up Recommended</label>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOutcomeModalOpen(false)}>Cancel</Button>
              <Button onClick={saveOutcome}>Save Outcome & Complete</Button>
            </div>
          </div>
        </div>
      )}

      <SafetyNote text="The timeline and outcome system chronologically records all clinical events without overwriting history." />
    </AppShell>
  );
}
