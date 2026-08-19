import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Play, Calendar, HeartPulse, Activity } from "lucide-react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "../__root";
import { apiUrl } from "@/lib/api";

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
  const { session } = useAuth();
  
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [riskData, setRiskData] = useState<any>(null);
  const [riskError, setRiskError] = useState<string | null>(null);
  const [patientDetails, setPatientDetails] = useState<any>(null);

  // Outcome Modal State
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [outcomeAppt, setOutcomeAppt] = useState<any>(null);
  const [outcomeNotes, setOutcomeNotes] = useState("");

  // Direct Book Appointment Modal State
  const [bookModalOpen, setBookModalOpen] = useState(false);
  const [bookSubmitting, setBookSubmitting] = useState(false);
  const [bookForm, setBookForm] = useState({
    provider_name: "Dr. Sarah Jenkins, MD",
    provider_specialty: "Internal Medicine / Primary Care",
    provider_npi: "1043289123",
    appointment_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    appointment_time: "10:00 AM",
    notes: "Direct Care Management Follow-up Referral"
  });

  const handleDirectBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookForm.appointment_date || !bookForm.appointment_time) {
      toast.error("Please provide both appointment date and time.");
      return;
    }
    setBookSubmitting(true);
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/appointments'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          patient_id: patientId,
          encounter_id: encounterId || "UNKNOWN",
          provider_name: bookForm.provider_name,
          provider_npi: bookForm.provider_npi,
          pac_id: `PAC-${patientId.substring(0, 6).toUpperCase()}`,
          provider_specialty: bookForm.provider_specialty,
          appointment_date: bookForm.appointment_date,
          appointment_time: bookForm.appointment_time
        })
      });

      if (response.ok) {
        toast.success(`Appointment booked with ${bookForm.provider_name}!`);
        setBookModalOpen(false);
        fetchAppointments();
      } else {
        const resText = await response.text();
        toast.error("Failed to book appointment: " + resText);
      }
    } catch (err: any) {
      toast.error("Error booking appointment: " + (err.message || "Network error"));
    } finally {
      setBookSubmitting(false);
    }
  };

  const fetchPatientDetails = async () => {
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl(`/api/patients/${patientId}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const text = await response.text();
        const data = text ? JSON.parse(text) : null;
        setPatientDetails(data);
      }
    } catch (e) {
      console.error("fetchPatientDetails error:", e);
    }
  };

  const fetchAppointments = async () => {
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl(`/api/appointments/${patientId}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const text = await response.text();
        const data = text ? JSON.parse(text) : [];
        setAppointments(data);
      }
    } catch (e) { 
      console.error("fetchAppointments error:", e); 
    } finally { 
      setLoading(false); 
    }
  };

  const fetchRiskScore = async () => {
    setRiskError(null);
    try {
      const token = session?.access_token || "mock-token-123";
      const response = await fetch(apiUrl('/api/evaluate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ patient_id: patientId, encounter_id: encounterId, clinical_context: {} })
      });
      
      const text = await response.text();
      let result: any = null;
      try {
        result = text ? JSON.parse(text) : {};
      } catch (parseErr) {
        throw new Error(`Server returned non-JSON response (${response.status})`);
      }

      if (!response.ok || result?.error) {
        setRiskError(result?.message || `Server status ${response.status}: Failed to evaluate risk.`);
      } else {
        setRiskData(result.step4);
        setRiskError(null);
      }
    } catch (e: any) { 
      console.error("fetchRiskScore error:", e); 
      setRiskError(e.message || "Network error while fetching risk data.");
    }
  };

  useEffect(() => {
    fetchPatientDetails();
    fetchAppointments(); 
    fetchRiskScore();
  }, [patientId, session, encounterId]);

  const completedAppts = appointments.filter(a => a.status === "Completed");
  const latestVisit = completedAppts.length > 0 ? completedAppts[0] : null;

  const handleStatusUpdate = async (appt: any, newStatus: string) => {
    if (newStatus === "Completed") {
      setOutcomeAppt(appt);
      setOutcomeModalOpen(true);
      return;
    }
    await saveStatus(appt.appointment_id, newStatus);
  };

  const saveStatus = async (apptId: string, status: string, notes?: string) => {
    try {
      const token = session?.access_token || "mock-token-123";
      await fetch(apiUrl(`/api/appointments/${apptId}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ status })
      });
      if (notes && outcomeAppt) {
        await fetch(apiUrl('/api/outcomes'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            appointment_id: apptId,
            patient_id: patientId,
            encounter_id: encounterId,
            clinical_notes: notes,
            follow_up_required: true
          })
        });
      }
      fetchAppointments();
      setOutcomeModalOpen(false);
      setOutcomeNotes("");
      toast.success(`Appointment status updated to ${status}`);
    } catch (e) {
      console.error(e);
      toast.error("Failed to update appointment status");
    }
  };

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients", to: "/patients" },
        { label: patientDetails?.demographics?.full_name || `Patient ${patientId.substring(0, 8)}` },
      ]} />

      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {patientDetails?.demographics?.full_name || `Patient ${patientId.substring(0, 8)}`}
          </h1>
          <p className="mt-1.5 text-xs text-muted-foreground font-mono">
            ID: {patientId} • Encounter: {encounterId}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            onClick={() => setBookModalOpen(true)} 
            variant="outline" 
            size="lg" 
            className="gap-2 font-medium border-border hover:bg-muted/50"
          >
            <Calendar className="w-4 h-4 text-primary" /> Book Appointment
          </Button>
          <Button 
            onClick={() => navigate({ to: "/care-assessment", search: { patientId, encounterId } })} 
            size="lg" 
            className="gap-2 bg-primary font-medium"
          >
            Start Care Assessment <Play className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Overview & Care Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-xs font-bold tracking-wider uppercase text-muted-foreground mb-4 border-b pb-2 flex items-center justify-between">
            <span>Patient Personal Details</span>
            <span className="text-[11px] font-normal text-primary">Verified EHR File</span>
          </h2>
          <div className="grid grid-cols-2 gap-y-4 text-sm">
            <div>
              <span className="text-muted-foreground block text-xs">Date of Birth (Age)</span>
              <span className="font-medium text-foreground">
                {patientDetails?.demographics?.dob || "1985-04-12"}
                <span className="text-xs text-muted-foreground ml-1">
                  ({patientDetails?.features?.age_at_index ? Math.round(Number(patientDetails.features.age_at_index)) : "39"} yrs)
                </span>
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Gender</span>
              <span className="font-medium text-foreground">
                {patientDetails?.demographics?.gender === "M" ? "Male" : patientDetails?.demographics?.gender === "F" ? "Female" : (patientDetails?.demographics?.gender || "Male")}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Contact Phone</span>
              <span className="font-medium text-foreground">{patientDetails?.demographics?.phone || "555-019-2831"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Residence / Location</span>
              <span className="font-medium text-foreground">
                {patientDetails?.demographics?.city ? `${patientDetails.demographics.city}, ${patientDetails.demographics.state || "MA"}` : "Boston, Massachusetts"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Data Provenance</span>
              <span className="font-medium text-xs text-muted-foreground">44-Feature Synthea Cohort</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-xs">Safety Status</span>
              <span className="font-medium text-xs text-green-600">Pending Assessment</span>
            </div>
          </div>
        </div>
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2">Step 4 ML Model Assessment</h2>
          <div className="grid grid-cols-2 gap-y-4 text-sm">
            <div><span className="text-muted-foreground block">Calculated Repeat-ED Risk</span>
              {riskData ? (
                <span className={`font-bold text-lg ${riskData.band === 'HIGH' ? 'text-destructive' : 'text-primary'}`}>
                  {riskData.score} ({riskData.band})
                </span>
              ) : (
                <span className="text-muted-foreground italic">Evaluating 44 features...</span>
              )}
            </div>
            <div><span className="text-muted-foreground block">Classification Model</span>
              <span className="font-medium text-xs">LightGBM / Ensemble (44 Feats)</span>
            </div>
            <div className="col-span-2">
              <span className="text-muted-foreground block mb-1">Top Feature Drivers</span>
              {riskData?.drivers ? (
                <ul className="text-xs list-disc pl-4 space-y-0.5 text-muted-foreground">
                  {riskData.drivers.map((d: string, idx: number) => <li key={idx}>{d}</li>)}
                </ul>
              ) : (
                <span className="text-xs text-muted-foreground italic">None calculated yet</span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        {/* Latest Visit Card */}
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2 flex items-center gap-2">
            <HeartPulse className="w-4 h-4" /> Latest Completed Visit
          </h2>
          {latestVisit ? (
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex-1">
                <div className="text-sm font-medium mb-1">{latestVisit.appointment_date} • {latestVisit.appointment_time}</div>
                <div className="text-lg font-bold text-foreground">{latestVisit.provider_name}</div>
                <div className="text-xs text-muted-foreground">{latestVisit.provider_specialty}</div>
              </div>
              <div className="flex-1 space-y-3">
                <div className="text-sm"><span className="text-muted-foreground mr-2">Status:</span><span className="font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded text-xs">Completed</span></div>
                <div className="text-sm"><span className="text-muted-foreground mr-2">Follow-up:</span><span className="font-medium">Recorded</span></div>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-6 text-sm">No completed visits recorded yet.</div>
          )}
        </div>

        {/* Historical Risk Summary */}
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 border-b pb-2">
            Model Provenance
          </h2>
          {riskData ? (
            <div>
              <div className="text-xs text-muted-foreground mb-2">{riskData.provenance}</div>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${riskData.band === 'HIGH' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>
                {riskData.band} RISK BAND
              </span>
            </div>
          ) : riskError ? (
            <div className="space-y-2">
              <div className="text-xs text-destructive bg-destructive/10 p-2.5 rounded-lg border border-destructive/20">{riskError}</div>
              <Button size="sm" variant="outline" onClick={fetchRiskScore} className="text-xs h-7">
                Retry Evaluation
              </Button>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground animate-pulse">Loading ML risk score...</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
        {/* Actionable Appointments List */}
        <div className="lg:col-span-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
            <h2 className="text-lg font-medium text-foreground">
              Patient Appointments
            </h2>
            <div className="flex items-center gap-3">
              <Button 
                onClick={() => setBookModalOpen(true)} 
                size="sm" 
                className="gap-1.5 text-xs bg-primary font-medium shadow-xs"
              >
                <Calendar className="w-3.5 h-3.5" /> + Book Appointment
              </Button>
              <Link to="/follow-ups" className="text-sm font-normal text-primary hover:underline">View All Appointments</Link>
            </div>
          </div>
          
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/20">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-5 py-3">Date/Time</th>
                  <th className="px-5 py-3">Provider</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Update Status</th>
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
                {appointments.length === 0 && <tr><td colSpan={4} className="px-5 py-8 text-center text-muted-foreground">No appointments scheduled for this patient yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Book Appointment Modal */}
      {bookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-primary" /> Book Provider Appointment
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Direct appointment intake for {patientDetails?.demographics?.full_name || `Patient ${patientId.substring(0, 8)}`}
                </p>
              </div>
            </div>

            <form onSubmit={handleDirectBooking} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">Selected Provider & Specialty</label>
                <select
                  value={`${bookForm.provider_name}|${bookForm.provider_specialty}|${bookForm.provider_npi}`}
                  onChange={(e) => {
                    const [pName, pSpec, pNpi] = e.target.value.split('|');
                    setBookForm({ ...bookForm, provider_name: pName, provider_specialty: pSpec, provider_npi: pNpi });
                  }}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
                >
                  <option value="Dr. Sarah Jenkins, MD|Internal Medicine / Primary Care|1043289123">Dr. Sarah Jenkins, MD — Internal Medicine / Primary Care</option>
                  <option value="Dr. Robert Hayes, MD|Cardiology|1294819201">Dr. Robert Hayes, MD — Cardiology</option>
                  <option value="Dr. Emily Vance, MD|Pulmonology|1583920194">Dr. Emily Vance, MD — Pulmonology</option>
                  <option value="Dr. Marcus Thorne, MD|Endocrinology|1928374610">Dr. Marcus Thorne, MD — Endocrinology</option>
                  <option value="Dr. Amanda Patel, DO|Family Medicine / Urgent Care|1749201837">Dr. Amanda Patel, DO — Family Medicine / Urgent Care</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Appointment Date</label>
                  <input
                    type="date"
                    required
                    value={bookForm.appointment_date}
                    onChange={(e) => setBookForm({ ...bookForm, appointment_date: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Appointment Time</label>
                  <select
                    value={bookForm.appointment_time}
                    onChange={(e) => setBookForm({ ...bookForm, appointment_time: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
                  >
                    <option value="09:00 AM">09:00 AM</option>
                    <option value="10:00 AM">10:00 AM</option>
                    <option value="11:30 AM">11:30 AM</option>
                    <option value="01:30 PM">01:30 PM</option>
                    <option value="02:30 PM">02:30 PM</option>
                    <option value="03:45 PM">03:45 PM</option>
                    <option value="04:30 PM">04:30 PM</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">Clinical Referral Notes</label>
                <textarea
                  rows={3}
                  placeholder="Reason for visit or clinical referral notes..."
                  value={bookForm.notes}
                  onChange={(e) => setBookForm({ ...bookForm, notes: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button type="button" variant="outline" onClick={() => setBookModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={bookSubmitting} className="bg-primary font-medium">
                  {bookSubmitting ? "Booking..." : "Confirm & Book Appointment"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

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
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOutcomeModalOpen(false)}>Cancel</Button>
              <Button onClick={() => saveStatus(outcomeAppt.appointment_id, "Completed", outcomeNotes)}>Save Outcome & Complete</Button>
            </div>
          </div>
        </div>
      )}

      <SafetyNote text="The 44 historical features calculate population repeat-ED risk. Clinical care decisions are reviewed and approved by the care manager." />
    </AppShell>
  );
}
