import { useState, useEffect } from 'react'
import { supabase } from '../supabase'
import { Calendar, User, FileText, CheckCircle, Clock } from 'lucide-react'

export default function PatientDashboard({ session }) {
  const [patientId, setPatientId] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 1. Get the patient ID linked to this profile
    const fetchPatientData = async () => {
      try {
        const { data: patientData, error: patientError } = await supabase
          .from('patients')
          .select('patient_id, name')
          .eq('profile_id', session.user.id)
          .single()

        if (patientData) {
          setPatientId(patientData.patient_id)
          fetchAppointments(patientData.patient_id)
        } else {
          setLoading(false)
        }
      } catch (e) {
        console.error(e)
        setLoading(false)
      }
    }

    fetchPatientData()
  }, [session.user.id])

  const fetchAppointments = async (pid) => {
    try {
      const response = await fetch(`http://localhost:8000/api/appointments/${pid}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      })
      if (response.ok) {
        setAppointments(await response.json())
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="p-12 text-center text-gray-500">Loading patient portal...</div>
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-8 bg-indigo-600 rounded-lg p-6 text-white shadow-md">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><User className="w-8 h-8"/> My Health Portal</h1>
          <p className="mt-2 text-indigo-100">Welcome to your secure patient dashboard.</p>
        </div>
        <button onClick={() => supabase.auth.signOut()} className="px-4 py-2 border border-white/30 rounded-md text-sm font-medium hover:bg-white/10 transition">
          Sign Out
        </button>
      </div>

      {!patientId ? (
        <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center">
          <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-900">Account Activation Pending</h2>
          <p className="text-gray-500 mt-2">Your account has not yet been linked to an EHR patient record by your care manager. Please check back later.</p>
        </div>
      ) : (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Calendar className="w-6 h-6 text-indigo-600"/> Upcoming & Past Appointments</h2>
          
          {appointments.length === 0 ? (
            <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center text-gray-500">
              No appointments found.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {appointments.map((appt) => (
                <div key={appt.appointment_id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex flex-col">
                  <div className="flex justify-between items-start mb-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${appt.status === 'Completed' ? 'bg-green-100 text-green-800' : appt.status === 'Scheduled' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                      {appt.status}
                    </span>
                    <div className="text-sm text-gray-500 text-right">
                      <div className="font-bold text-gray-900">{appt.appointment_date}</div>
                      <div>{appt.appointment_time}</div>
                    </div>
                  </div>
                  
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900">{appt.provider_name}</h3>
                    <p className="text-sm text-gray-600">{appt.provider_specialty}</p>
                  </div>
                  
                  {appt.status === 'Completed' && (
                    <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-600 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4 text-green-500"/> Post-consultation outcome recorded
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
