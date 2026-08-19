import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAuth } from "./__root";

export const Route = createFileRoute("/follow-ups")({
  head: () => ({ meta: [{ title: "Appointments & Follow-ups — CarePath" }] }),
  component: AppointmentsPage,
});

const STATUS_FILTERS = ["All", "Scheduled", "Rescheduled", "Completed", "No-Show", "Cancelled"] as const;

function AppointmentsPage() {
  const { session } = useAuth();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [rescheduleAppt, setRescheduleAppt] = useState<any>(null);
  const [cancelAppt, setCancelAppt] = useState<any>(null);
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const token = session?.access_token || "mock-token-123";
      const res = await fetch('/api/appointments', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const text = await res.text();
        const data = text ? JSON.parse(text) : [];
        setAppointments(data);
      }
    } catch (e) {
      console.warn("Appointments fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [session]);

  const filteredAppointments = activeFilter === "All"
    ? appointments
    : appointments.filter(a => a.status === activeFilter);

  const handleStatusChange = (appt: any, e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "Reschedule") {
      setRescheduleAppt(appt);
      setNewDate(appt.appointment_date);
      setNewTime(appt.appointment_time);
      e.target.value = appt.status;
    } else if (val === "Cancel") {
      setCancelAppt(appt);
      e.target.value = appt.status;
    } else if (val === "Completed" || val === "No-Show") {
      updateStatus(appt.appointment_id, val);
    }
  };

  const updateStatus = async (apptId: string, status: string, date?: string, time?: string) => {
    try {
      const token = session?.access_token || "mock-token-123";
      const body: any = { status };
      if (date && time) {
        body.appointment_date = date;
        body.appointment_time = time;
      }
      await fetch(`/api/appointments/${apptId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body)
      });
      toast.success(`Appointment status updated to ${status}`);
      fetchAppointments();
    } catch (e) {
      toast.error("Failed to update status");
    }
  };

  const confirmReschedule = async () => {
    if (!newDate || !newTime) {
      toast.error("Date and time are required.");
      return;
    }
    await updateStatus(rescheduleAppt.appointment_id, "Rescheduled", newDate, newTime);
    setRescheduleAppt(null);
  };

  const confirmCancel = async () => {
    await updateStatus(cancelAppt.appointment_id, "Cancelled");
    setCancelAppt(null);
  };

  // Count badges
  const counts: Record<string, number> = { All: appointments.length };
  STATUS_FILTERS.forEach(s => { if (s !== "All") counts[s] = appointments.filter(a => a.status === s).length; });

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Appointments & Follow-ups" },
      ]} />
      <PageHeader
        title="Appointments & Follow-ups"
        subtitle="Manage scheduled care, monitor outcomes, and track follow-up compliance."
      />

      {/* Status Filter Tabs */}
      <div className="mb-6 flex flex-wrap gap-1.5">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => setActiveFilter(status)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              activeFilter === status
                ? "border-primary/30 bg-primary/10 text-primary font-medium"
                : "border-border text-muted-foreground hover:bg-muted"
            )}
          >
            {status}
            <span className="ml-1.5 text-[10px] opacity-70">({counts[status] || 0})</span>
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-sm animate-pulse">Loading appointments...</div>
        ) : filteredAppointments.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">No appointments match this filter.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
                <th className="px-5 py-3.5">Patient</th>
                <th className="px-5 py-3.5">Provider / Specialty</th>
                <th className="px-5 py-3.5">Date & Time</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredAppointments.map((a, idx) => (
                <tr key={`${a.appointment_id}-${idx}`} className="hover:bg-muted/40 transition-colors">
                  <td className="px-5 py-4">
                    <Link to={`/patients/${a.patient_id}`} className="font-medium text-primary hover:underline block font-mono text-xs">
                      {a.patient_id.substring(0, 16)}...
                    </Link>
                    <span className="text-xs text-muted-foreground">{a.encounter_id ? `Enc: ${a.encounter_id.substring(0, 10)}...` : ""}</span>
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
                    {(a.status === "Scheduled" || a.status === "Rescheduled") && (
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
                    )}
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

      <div className="mt-8">
        <SafetyNote text="This recommendation is based on historical utilization and does not determine whether a current condition is an emergency. If you are experiencing severe or life-threatening symptoms, seek emergency care." />
      </div>
    </AppShell>
  );
}
