import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/follow-ups")({
  head: () => ({ meta: [{ title: "Appointments & Follow-ups — CarePath" }] }),
  component: AppointmentsPage,
});

// ── Mock appointments ──
const MOCK_APPOINTMENTS = [
  { appointment_id: "appt-101", patient_id: "p-1042", provider_name: "Riverbend Family Medicine", provider_specialty: "Family Medicine", appointment_date: "2026-08-25", appointment_time: "10:00 AM", status: "Scheduled" },
  { appointment_id: "appt-102", patient_id: "p-1130", provider_name: "Cedar Street Urgent Care", provider_specialty: "Urgent Care", appointment_date: "2026-08-23", appointment_time: "2:00 PM", status: "Scheduled" },
  { appointment_id: "appt-103", patient_id: "p-1188", provider_name: "CarePath Virtual Clinic", provider_specialty: "Telehealth", appointment_date: "2026-08-22", appointment_time: "11:30 AM", status: "Scheduled" },
  { appointment_id: "appt-104", patient_id: "p-1204", provider_name: "Northside Community Health", provider_specialty: "Internal Medicine", appointment_date: "2026-08-20", appointment_time: "9:00 AM", status: "Rescheduled" },
  { appointment_id: "appt-105", patient_id: "p-1042", provider_name: "Dr. Sarah Williams", provider_specialty: "Internal Medicine", appointment_date: "2026-08-12", appointment_time: "2:30 PM", status: "Completed" },
  { appointment_id: "appt-106", patient_id: "p-1256", provider_name: "Riverbend Family Medicine", provider_specialty: "Family Medicine", appointment_date: "2026-08-10", appointment_time: "10:00 AM", status: "Completed" },
  { appointment_id: "appt-107", patient_id: "p-1130", provider_name: "Cedar Street Urgent Care", provider_specialty: "Urgent Care", appointment_date: "2026-08-08", appointment_time: "3:00 PM", status: "No-Show" },
  { appointment_id: "appt-108", patient_id: "p-1188", provider_name: "Population Health Care Team", provider_specialty: "Care Management", appointment_date: "2026-08-05", appointment_time: "1:00 PM", status: "Completed" },
  { appointment_id: "appt-109", patient_id: "p-1301", provider_name: "CarePath Virtual Clinic", provider_specialty: "Telehealth", appointment_date: "2026-07-28", appointment_time: "4:00 PM", status: "Cancelled" },
];

const PATIENT_NAMES: Record<string, string> = {
  "p-1042": "Marcus Bell",
  "p-1130": "Alina Okafor",
  "p-1188": "Robert Chen",
  "p-1204": "Denise Hartley",
  "p-1256": "Javier Ruiz",
  "p-1301": "Grace Lindqvist",
};

const STATUS_FILTERS = ["All", "Scheduled", "Rescheduled", "Completed", "No-Show", "Cancelled"] as const;

function AppointmentsPage() {
  const [appointments, setAppointments] = useState(MOCK_APPOINTMENTS);
  const [activeFilter, setActiveFilter] = useState<string>("All");

  // Modal states
  const [rescheduleAppt, setRescheduleAppt] = useState<any>(null);
  const [cancelAppt, setCancelAppt] = useState<any>(null);
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");

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
      setAppointments(prev => prev.map(a => a.appointment_id === appt.appointment_id ? { ...a, status: val } : a));
      toast.success(`Appointment marked as ${val}`);
    }
  };

  const confirmReschedule = () => {
    if (!newDate || !newTime) {
      toast.error("Date and time are required.");
      return;
    }
    setAppointments(prev => prev.map(a =>
      a.appointment_id === rescheduleAppt.appointment_id
        ? { ...a, status: "Rescheduled", appointment_date: newDate, appointment_time: newTime }
        : a
    ));
    toast.success("Appointment rescheduled");
    setRescheduleAppt(null);
  };

  const confirmCancel = () => {
    setAppointments(prev => prev.map(a =>
      a.appointment_id === cancelAppt.appointment_id ? { ...a, status: "Cancelled" } : a
    ));
    toast.success("Appointment cancelled");
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
        {filteredAppointments.length === 0 ? (
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
                    <Link to={`/patients/${a.patient_id}`} className="font-medium text-primary hover:underline block">
                      {PATIENT_NAMES[a.patient_id] || `Patient ${a.patient_id.substring(0, 8)}`}
                    </Link>
                    <span className="text-xs text-muted-foreground">{a.patient_id}</span>
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
            <p className="text-sm text-muted-foreground mb-4">Select a new date and time for {PATIENT_NAMES[rescheduleAppt.patient_id] || rescheduleAppt.patient_id}.</p>
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
