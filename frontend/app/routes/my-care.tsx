import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { useState, useEffect } from "react";
import { Calendar, User, Activity, Clock, ShieldCheck, HeartPulse } from "lucide-react";
import { useAuth } from "./__root";
import * as Dialog from "@radix-ui/react-dialog";

export const Route = createFileRoute("/my-care")({
  head: () => ({
    meta: [{ title: "My Care Dashboard — CarePath" }],
  }),
  component: PatientDashboard,
});

function PatientDashboard() {
  const { patientToken, role } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isRescheduleOpen, setIsRescheduleOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<any>(null);
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");

  const fetchData = async () => {
    try {
      if (!patientToken) return;

      const profileRes = await fetch("/api/patient/profile", {
        headers: { "Authorization": `Bearer patient-${patientToken}` }
      });
      if (profileRes.ok) setProfile(await profileRes.json());

      const apptsRes = await fetch("/api/patient/appointments", {
        headers: { "Authorization": `Bearer patient-${patientToken}` }
      });
      if (apptsRes.ok) {
        const data = await apptsRes.json();
        setAppointments(data.appointments || []);
        setOutcomes(data.outcomes || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [patientToken]);

  const handleReschedule = async () => {
    if (!selectedAppt || !newDate || !newTime) return;
    try {
      await fetch(`/api/patient/appointments/${selectedAppt.appointment_id}/reschedule`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer patient-${patientToken}` 
        },
        body: JSON.stringify({ new_date: newDate, new_time: newTime })
      });
      setIsRescheduleOpen(false);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancel = async () => {
    if (!selectedAppt) return;
    try {
      await fetch(`/api/patient/appointments/${selectedAppt.appointment_id}/cancel`, {
        method: "POST",
        headers: { "Authorization": `Bearer patient-${patientToken}` }
      });
      setIsCancelOpen(false);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  if (role !== "PATIENT") {
    return (
      <AppShell>
        <div className="p-8 text-center text-muted-foreground">
          Patient Portal access only.
        </div>
      </AppShell>
    );
  }

  if (loading) {
    return <AppShell><div className="p-12 text-center animate-pulse">Loading Patient Portal...</div></AppShell>;
  }

  const upcomingAppts = appointments.filter(a => a.status === "Scheduled" || a.status === "Rescheduled");
  const pastAppts = appointments.filter(a => a.status !== "Scheduled" && a.status !== "Rescheduled");
  const nextAppt = upcomingAppts.length > 0 ? upcomingAppts[0] : null;
  const latestOutcome = outcomes.length > 0 ? outcomes[0] : null;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Welcome, {profile?.name}</h1>
          <p className="text-sm text-muted-foreground mt-1">Patient ID: {profile?.patient_id}</p>
          
          <div className="mt-6 pt-6 border-t border-border grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="block text-muted-foreground text-xs uppercase mb-1">Date of Birth</span><span className="font-medium">{profile?.dob}</span></div>
            <div><span className="block text-muted-foreground text-xs uppercase mb-1">Age</span><span className="font-medium">{profile?.age}</span></div>
            <div><span className="block text-muted-foreground text-xs uppercase mb-1">Gender</span><span className="font-medium capitalize">{profile?.gender}</span></div>
            <div><span className="block text-muted-foreground text-xs uppercase mb-1">Phone</span><span className="font-medium">{profile?.phone}</span></div>
          </div>
        </div>

        {/* Latest Visit & Next Appointment Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Latest Visit */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 flex items-center gap-2 border-b pb-2">
              <Activity className="w-4 h-4" /> Latest Visit
            </h2>
            {latestOutcome ? (
              <div className="space-y-3 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Date:</span> <span className="font-medium">{latestOutcome.consultation_date}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Provider:</span> <span className="font-medium">{latestOutcome.provider_name}</span></div>
                <div><span className="text-muted-foreground block mb-1">Reason:</span> <span className="font-medium">{latestOutcome.clinical_notes || "Not available"}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Outcome:</span> <span className="font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded text-xs">Completed</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Care Pathway:</span> <span className="font-medium">{latestOutcome.follow_up_plan || "Routine Care"}</span></div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No recent visit information available.</p>
            )}
          </div>

          {/* Next Appointment */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground mb-4 flex items-center gap-2 border-b pb-2">
                <Calendar className="w-4 h-4" /> Upcoming Appointment
              </h2>
              {nextAppt ? (
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">Provider:</span> <span className="font-medium text-primary">{nextAppt.provider_name}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Date:</span> <span className="font-medium">{nextAppt.appointment_date}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Time:</span> <span className="font-medium">{nextAppt.appointment_time}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Type:</span> <span className="font-medium">{nextAppt.care_type || "General"}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Status:</span> <span className="font-medium text-blue-600">{nextAppt.status}</span></div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No upcoming appointments.</p>
              )}
            </div>
            
            {nextAppt && (
              <div className="mt-6 flex gap-3">
                <button 
                  onClick={() => { setSelectedAppt(nextAppt); setIsRescheduleOpen(true); }}
                  className="flex-1 bg-muted hover:bg-muted/80 text-foreground text-sm font-medium py-2 rounded-lg transition-colors border border-border"
                >
                  Reschedule
                </button>
                <button 
                  onClick={() => { setSelectedAppt(nextAppt); setIsCancelOpen(true); }}
                  className="flex-1 bg-destructive/10 hover:bg-destructive/20 text-destructive text-sm font-medium py-2 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Appointment History */}
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="p-6 border-b border-border">
             <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground flex items-center gap-2">
              <Clock className="w-4 h-4" /> Appointment History
            </h2>
          </div>
          {pastAppts.length === 0 ? (
             <div className="p-8 text-center text-sm text-muted-foreground">No previous appointments available.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/20">
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="px-6 py-3 font-medium">Date & Time</th>
                  <th className="px-6 py-3 font-medium">Provider</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pastAppts.map(a => (
                  <tr key={a.appointment_id} className="hover:bg-muted/40">
                    <td className="px-6 py-4">{a.appointment_date} {a.appointment_time}</td>
                    <td className="px-6 py-4">{a.provider_name}</td>
                    <td className="px-6 py-4">{a.care_type || "Follow-up"}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs ${a.status === 'Completed' ? 'bg-green-100 text-green-800' : a.status === 'Cancelled' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </div>

      {/* Reschedule Modal */}
      <Dialog.Root open={isRescheduleOpen} onOpenChange={setIsRescheduleOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm bg-background rounded-xl p-6 shadow-xl z-50 border border-border">
            <Dialog.Title className="text-lg font-semibold mb-4">Reschedule Appointment</Dialog.Title>
            {selectedAppt && (
              <div className="space-y-4">
                <div className="text-sm bg-muted/30 p-3 rounded-lg border border-border">
                  <p className="text-muted-foreground text-xs mb-1">Current Appointment</p>
                  <p className="font-medium">{selectedAppt.appointment_date} — {selectedAppt.appointment_time}</p>
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">New Date</label>
                  <input 
                    type="date" 
                    value={newDate} 
                    onChange={e => setNewDate(e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-input text-sm" 
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">New Time</label>
                  <input 
                    type="time" 
                    value={newTime} 
                    onChange={e => setNewTime(e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-input text-sm" 
                  />
                </div>

                <div className="flex gap-3 mt-6">
                  <button onClick={() => setIsRescheduleOpen(false)} className="flex-1 px-4 py-2 text-sm border border-input rounded-md hover:bg-muted">Cancel</button>
                  <button onClick={handleReschedule} disabled={!newDate || !newTime} className="flex-1 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50">Confirm Reschedule</button>
                </div>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Cancel Modal */}
      <Dialog.Root open={isCancelOpen} onOpenChange={setIsCancelOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm bg-background rounded-xl p-6 shadow-xl z-50 border border-border">
            <Dialog.Title className="text-lg font-semibold mb-2">Cancel Appointment?</Dialog.Title>
            <Dialog.Description className="text-sm text-muted-foreground mb-6">
              Are you sure you want to cancel this appointment? This action cannot be undone.
            </Dialog.Description>
            {selectedAppt && (
              <div className="space-y-4">
                <div className="text-sm bg-destructive/5 text-destructive p-3 rounded-lg border border-destructive/20 text-center">
                  <p className="font-medium">{selectedAppt.appointment_date} at {selectedAppt.appointment_time}</p>
                  <p>{selectedAppt.provider_name}</p>
                </div>

                <div className="flex flex-col gap-2 mt-6">
                  <button onClick={handleCancel} className="w-full px-4 py-2 text-sm bg-destructive text-destructive-foreground font-medium rounded-md hover:bg-destructive/90">Confirm Cancellation</button>
                  <button onClick={() => setIsCancelOpen(false)} className="w-full px-4 py-2 text-sm border border-input font-medium rounded-md hover:bg-muted">Keep Appointment</button>
                </div>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

    </AppShell>
  );
}
