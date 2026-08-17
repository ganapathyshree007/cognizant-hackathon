import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { SAFETY_NOTE } from "@/lib/mock-data";
import { useAuth } from "./__root";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/follow-ups")({
  head: () => ({ meta: [{ title: "Appointments & Follow-ups — CarePath" }] }),
  component: AppointmentsPage,
});

function AppointmentsPage() {
  const { session } = useAuth();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [rescheduleAppt, setRescheduleAppt] = useState<any>(null);
  const [cancelAppt, setCancelAppt] = useState<any>(null);
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");
  const [reason, setReason] = useState("");

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/appointments`, {
        headers: { 'Authorization': `Bearer ${session?.access_token}` }
      });
      if (response.ok) setAppointments(await response.json());
    } catch (e) { console.error(e); } 
    finally { setLoading(false); }
  };

  useEffect(() => { if (session?.access_token) fetchAppointments(); }, [session]);

  const handleStatusChange = (appt: any, e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "Reschedule") {
      setRescheduleAppt(appt);
      setNewDate(appt.appointment_date);
      setNewTime(appt.appointment_time);
      e.target.value = appt.status; // Reset select visually
    } else if (val === "Cancel") {
      setCancelAppt(appt);
      e.target.value = appt.status; // Reset
    } else if (val === "Completed" || val === "No-Show") {
      updateApptStatus(appt.appointment_id, val);
    }
  };

  const updateApptStatus = async (apptId: string, newStatus: string, date?: string, time?: string) => {
    try {
      const body: any = { status: newStatus };
      if (date && time) { body.appointment_date = date; body.appointment_time = time; }
      
      await fetch(`/api/appointments/${apptId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${session?.access_token}` },
        body: JSON.stringify(body)
      });
      fetchAppointments();
    } catch(e) { console.error(e); }
  };

  const confirmReschedule = async () => {
    if (!newDate || !newTime) return alert("Date and time are required.");
    await updateApptStatus(rescheduleAppt.appointment_id, "Rescheduled", newDate, newTime);
    setRescheduleAppt(null);
  };

  const confirmCancel = async () => {
    await updateApptStatus(cancelAppt.appointment_id, "Cancelled");
    setCancelAppt(null);
  };

  return (
    <AppShell>
      <PageHeader
        title="Appointments & Follow-ups"
        subtitle="Manage scheduled care, monitor outcomes, and track follow-up compliance."
      />

      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading appointments...</div>
        ) : appointments.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">No appointments found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
                <th className="px-5 py-3.5">Patient</th>
                <th className="px-5 py-3.5">Provider / Hospital</th>
                <th className="px-5 py-3.5">Date & Time</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {appointments.map((a, idx) => (
                <tr key={`${a.appointment_id}-${idx}`} className="hover:bg-muted/40 transition-colors">
                  <td className="px-5 py-4">
                    <Link to={`/patients/${a.patient_id}`} className="font-medium text-primary hover:underline block">
                      Patient {a.patient_id.substring(0, 8)}
                    </Link>
                    <span className="text-xs text-muted-foreground">ID: {a.patient_id}</span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="font-medium text-foreground">{a.provider_name}</div>
                    <div className="text-xs text-muted-foreground">{a.provider_specialty}</div>
                  </td>
                  <td className="px-5 py-4 text-foreground">
                    {a.appointment_date} <br/>
                    <span className="text-xs text-muted-foreground">{a.appointment_time}</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      a.status === 'Completed' ? 'bg-green-100 text-green-800' : 
                      a.status === 'Rescheduled' ? 'bg-purple-100 text-purple-800' :
                      (a.status === 'Cancelled' || a.status === 'No-Show' ? 'bg-destructive/10 text-destructive' : 'bg-blue-100 text-blue-800')
                    }`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <select 
                      onChange={(e) => handleStatusChange(a, e)} 
                      value={a.status} 
                      className="flex h-8 w-full max-w-[140px] rounded-md border border-input bg-background px-2 text-xs shadow-sm"
                    >
                      <option value="Scheduled">Scheduled</option>
                      <option value="Completed">Mark Completed</option>
                      <option value="No-Show">Mark No-Show</option>
                      <option value="Cancel">Cancel</option>
                      <option value="Reschedule">Reschedule</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Reschedule Modal */}
      {rescheduleAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold mb-2">Reschedule Appointment</h3>
            <p className="text-sm text-muted-foreground mb-4">Select a new date and time for Patient {rescheduleAppt.patient_id.substring(0,8)}.</p>
            <div className="space-y-4 mb-6">
              <div>
                <label className="text-xs font-medium mb-1 block">New Date</label>
                <Input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">New Time</label>
                <Input type="time" value={newTime} onChange={e => setNewTime(e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">Reason (Optional)</label>
                <Input type="text" placeholder="e.g., Patient requested..." value={reason} onChange={e => setReason(e.target.value)} />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRescheduleAppt(null)}>Cancel</Button>
              <Button onClick={confirmReschedule}>Confirm Reschedule</Button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {cancelAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-destructive/20 bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-destructive mb-2">Cancel Appointment?</h3>
            <p className="text-sm text-muted-foreground mb-6">
              This action will mark the appointment as cancelled. The history will be preserved. Are you sure?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCancelAppt(null)}>Keep Appointment</Button>
              <Button variant="destructive" onClick={confirmCancel}>Yes, Cancel Appointment</Button>
            </div>
          </div>
        </div>
      )}

    </AppShell>
  );
}
