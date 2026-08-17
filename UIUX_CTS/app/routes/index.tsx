import { createFileRoute } from "@tanstack/react-router";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Users, ActivitySquare, CalendarDays, PhoneCall } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useAuth } from "./__root";

export const Route = createFileRoute("/")({
  component: DashboardOverview,
});

function DashboardOverview() {
  const { session } = useAuth();
  const [stats, setStats] = useState({
    total_patients: 0,
    needing_assessment: 0,
    upcoming_appointments: 0,
    follow_ups_due: 0
  });
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const statsRes = await fetch('/api/dashboard/stats', {
          headers: { 'Authorization': `Bearer ${session?.access_token}` }
        });
        if (statsRes.ok) {
          setStats(await statsRes.json());
        }

        const apptsRes = await fetch('/api/appointments', {
          headers: { 'Authorization': `Bearer ${session?.access_token}` }
        });
        if (apptsRes.ok) {
          const apptsData = await apptsRes.json();
          // Show only top 5 upcoming/scheduled appointments
          const upcoming = apptsData.filter((a: any) => a.status === 'Scheduled').slice(0, 5);
          setAppointments(upcoming);
        }
      } catch (e) {
        console.error("Dashboard fetch error:", e);
      } finally {
        setLoading(false);
      }
    };

    if (session?.access_token) {
      fetchDashboard();
    }
  }, [session]);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        subtitle="Care Manager Overview."
      />
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm flex flex-col gap-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="w-4 h-4" />
            <span className="text-sm font-medium">Total Active Patients</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {loading ? "..." : stats.total_patients}
          </div>
        </div>

        <div className="bg-card border border-border p-6 rounded-xl shadow-sm flex flex-col gap-2">
          <div className="flex items-center gap-2 text-destructive">
            <ActivitySquare className="w-4 h-4" />
            <span className="text-sm font-medium">Needing Assessment</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {loading ? "..." : stats.needing_assessment}
          </div>
        </div>

        <div className="bg-card border border-border p-6 rounded-xl shadow-sm flex flex-col gap-2">
          <div className="flex items-center gap-2 text-blue-500">
            <CalendarDays className="w-4 h-4" />
            <span className="text-sm font-medium">Upcoming Appointments</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {loading ? "..." : stats.upcoming_appointments}
          </div>
        </div>

        <div className="bg-card border border-border p-6 rounded-xl shadow-sm flex flex-col gap-2">
          <div className="flex items-center gap-2 text-amber-500">
            <PhoneCall className="w-4 h-4" />
            <span className="text-sm font-medium">Follow-ups Due</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {loading ? "..." : stats.follow_ups_due}
          </div>
        </div>
      </div>

      {/* Recent Appointments */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-foreground">Upcoming Appointments</h2>
          <Link to="/follow-ups" className="text-sm text-primary hover:underline">View All</Link>
        </div>
        
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground text-sm">Loading appointments...</div>
          ) : appointments.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-sm">No upcoming appointments scheduled.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/20">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-5 py-3">Date & Time</th>
                  <th className="px-5 py-3">Patient ID</th>
                  <th className="px-5 py-3">Provider</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {appointments.map((a) => (
                  <tr key={a.appointment_id} className="hover:bg-muted/40 transition-colors">
                    <td className="px-5 py-4 whitespace-nowrap text-foreground font-medium">
                      {a.appointment_date} at {a.appointment_time}
                    </td>
                    <td className="px-5 py-4 text-muted-foreground">
                      <Link to={`/patients/${a.patient_id}`} className="hover:underline text-primary">
                        {a.patient_id}
                      </Link>
                    </td>
                    <td className="px-5 py-4 text-muted-foreground">{a.provider_name}</td>
                    <td className="px-5 py-4">
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
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
    </AppShell>
  );
}
