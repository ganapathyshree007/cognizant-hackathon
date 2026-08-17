import { useState, useEffect } from 'react'
import { supabase } from '../supabase'
import { Search, UserCircle, Activity, AlertTriangle, CheckCircle, FileText, Calendar, ChevronRight } from 'lucide-react'

export default function CareManagerDashboard({ session }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedEncounter, setSelectedEncounter] = useState(null)
  
  const [clinicalForm, setClinicalForm] = useState({
    "SpO2": "", "Heart Rate": "", "Respiratory Rate": "", "Systolic BP": "", "Temperature": "", "AVPU": "", "Pain": "",
    "Chest Pain": "", "Bleeding": "", "Convulsions": "", "Allergic Reaction": "", "Active High-Risk Condition": "", "Safety Conflict": "", "required_specialty_hint": ""
  })
  
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [auditReason, setAuditReason] = useState("")
  const [approved, setApproved] = useState(false)
  
  const [appointments, setAppointments] = useState([])
  const [apptForm, setApptForm] = useState({ date: "", time: "", selectedProviderIndex: 0 })
  const [outcomes, setOutcomes] = useState([])
  
  const [activeOutcomeApptId, setActiveOutcomeApptId] = useState(null)
  const [outcomeForm, setOutcomeForm] = useState({ notes: "", followUp: false })

  const token = session.access_token

  const handleSearch = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/patients/search?query=${searchQuery}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setSearchResults(await response.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  const selectPatientEncounter = (patientId, encounterId) => {
    setSelectedEncounter({ patientId, encounterId })
    fetchPatientData(patientId, encounterId, false)
    fetchAppointments(patientId)
  }

  const fetchPatientData = async (pid, eid, isStage2 = false) => {
    setLoading(true)
    setError(null)
    if (!isStage2) { setData(null); setExplanation(null); setApproved(false); }
    
    const contextToSend = {}
    if (isStage2) {
      Object.keys(clinicalForm).forEach(key => {
        if (clinicalForm[key] !== "") {
          const val = clinicalForm[key]
          if (!isNaN(val) && val.trim() !== "") contextToSend[key] = Number(val)
          else if (val === "true" || val === "Yes") contextToSend[key] = true
          else if (val === "false" || val === "No") contextToSend[key] = false
          else contextToSend[key] = val
        }
      })
    }
    
    try {
      const response = await fetch('http://localhost:8000/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ patient_id: pid, encounter_id: eid, clinical_context: contextToSend })
      })
      const result = await response.json()
      if (result.error) setError(result)
      else {
        setData(result)
        if (isStage2 && result.step5?.status !== "PENDING") {
          fetchExplanation(result, contextToSend)
        }
      }
    } catch (e) {
      setError({ message: e.message, error: "CONNECTION_ERROR" })
    }
    setLoading(false)
  }

  const fetchExplanation = async (resultData, contextToSend) => {
    try {
      const response = await fetch('http://localhost:8000/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          step4: resultData.step4 || {}, step5: resultData.step5 || {},
          step6: resultData.step6 || {}, step7: resultData.step7 || {},
          clinical_context: contextToSend 
        })
      })
      const expRes = await response.json()
      setExplanation(expRes.explanation)
    } catch (e) { console.error(e) }
  }
  
  const fetchAppointments = async (pid) => {
    try {
      const response = await fetch(`http://localhost:8000/api/appointments/${pid}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setAppointments(await response.json())
      }
      
      // Fetch outcomes directly from Supabase for this patient
      const { data: outcomeData } = await supabase
        .from('outcomes')
        .select('*')
        .eq('patient_id', pid)
        .order('created_at', { ascending: false })
      if (outcomeData) setOutcomes(outcomeData)
        
    } catch (e) { console.error(e) }
  }

  const handleDecision = async (action) => {
    if ((action === "REJECT" || action === "ESCALATE") && !auditReason) {
      alert(`A reason is required to ${action}.`)
      return
    }
    try {
      const response = await fetch('http://localhost:8000/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          patient_id: selectedEncounter.patientId, encounter_id: selectedEncounter.encounterId,
          action: action, reason: auditReason || "Approved",
          system_pathway: data?.step6?.Pathway || "N/A",
          system_provider: data?.step7?.Options?.[0]?.Name || "NONE",
          selected_provider: data?.step7?.Options?.[0]?.Name || "NONE"
        })
      })
      if (response.ok) {
        alert(`Decision ${action} recorded!`)
        setAuditReason("")
        if (action === "APPROVE") setApproved(true)
      }
    } catch (e) { alert("Error saving audit trail.") }
  }

  const handleScheduleAppt = async () => {
    if (!apptForm.date || !apptForm.time) return alert("Select date and time.")
    const provider = data.step7.Options[apptForm.selectedProviderIndex]
    try {
      const response = await fetch('http://localhost:8000/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          patient_id: selectedEncounter.patientId, encounter_id: selectedEncounter.encounterId,
          provider_name: provider.Name, provider_npi: String(provider.NPI || "N/A"), pac_id: String(provider.PAC_ID || "N/A"),
          provider_specialty: provider.Specialty, appointment_date: apptForm.date, appointment_time: apptForm.time
        })
      })
      if (response.ok) {
        alert("Appointment created successfully! (Integration Point)")
        fetchAppointments(selectedEncounter.patientId)
      }
    } catch (e) { alert("Failed to schedule appointment.") }
  }
  
  const updateApptStatus = async (apptId, newStatus) => {
    try {
      const response = await fetch(`http://localhost:8000/api/appointments/${apptId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ status: newStatus })
      })
      if (response.ok) {
        fetchAppointments(selectedEncounter.patientId)
        if (newStatus === "Completed") {
          setActiveOutcomeApptId(apptId)
        }
      }
    } catch(e) { console.error(e) }
  }
  
  const submitOutcome = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/outcomes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          appointment_id: activeOutcomeApptId,
          patient_id: selectedEncounter.patientId,
          encounter_id: selectedEncounter.encounterId,
          clinical_notes: outcomeForm.notes,
          follow_up_required: outcomeForm.followUp
        })
      })
      if (response.ok) {
        alert("Outcome Captured Successfully! Patient Record Updated.")
        setActiveOutcomeApptId(null)
        setOutcomeForm({ notes: "", followUp: false })
        fetchAppointments(selectedEncounter.patientId)
      }
    } catch(e) { console.error(e) }
  }

  const handleGenerateReport = async () => {
    try {
        const response = await fetch(`http://localhost:8000/api/report/${selectedEncounter.patientId}/${selectedEncounter.encounterId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `CareAssessment_${selectedEncounter.patientId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } else {
            alert("Failed to generate report.")
        }
    } catch (e) {
        console.error(e)
    }
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2"><Activity className="w-8 h-8 text-indigo-600"/> Care Manager Dashboard</h1>
          <p className="text-gray-500 mt-1">Select an encounter and run the clinical orchestration workflow.</p>
        </div>
        <button onClick={() => supabase.auth.signOut()} className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">
          Sign Out
        </button>
      </div>

      {/* SEARCH SECTION */}
      {!selectedEncounter && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2"><Search className="w-5 h-5"/> Search Patient History</h2>
          <div className="flex gap-4 mb-6">
            <input 
              type="text" 
              placeholder="Enter Patient ID or Name" 
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 py-2 px-3 border"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button onClick={handleSearch} className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 transition">Search</button>
          </div>

          {searchResults.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patient ID</th>
                    <th className="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Encounter ID</th>
                    <th className="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {searchResults.map((r, i) => (
                    <tr key={i}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{r.PATIENT_ID}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.ENCOUNTER_ID}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.INDEX_TIMESTAMP}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button onClick={() => selectPatientEncounter(r.PATIENT_ID, r.ENCOUNTER_ID)} className="text-indigo-600 hover:text-indigo-900 flex items-center gap-1">
                          Select <ChevronRight className="w-4 h-4"/>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* DASHBOARD CONTENT */}
      {selectedEncounter && (
        <div className="space-y-6">
          <div className="bg-white px-4 py-5 border-b border-gray-200 sm:px-6 flex justify-between items-center rounded-t-lg shadow-sm border">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">Active Orchestration</h3>
              <p className="mt-1 text-sm text-gray-500">Patient: <span className="font-mono">{selectedEncounter.patientId}</span> | Encounter: <span className="font-mono">{selectedEncounter.encounterId}</span></p>
            </div>
            <div className="flex gap-2">
                <button onClick={handleGenerateReport} className="bg-white text-gray-700 border border-gray-300 px-4 py-2 rounded-md hover:bg-gray-50 transition flex items-center gap-2">
                <FileText className="w-4 h-4"/> PDF Report
                </button>
                <button onClick={() => { setSelectedEncounter(null); setData(null); setAppointments([]); setOutcomes([]); }} className="text-gray-500 hover:text-gray-700">Change Patient</button>
            </div>
          </div>

          {error && <div className="bg-red-50 p-4 rounded-md text-red-700 flex items-center gap-2 border border-red-200"><AlertTriangle className="w-5 h-5"/> {error.message}</div>}
          
          {loading && !data && <div className="p-12 text-center text-gray-500 animate-pulse">Loading orchestration data...</div>}

          {/* HISTORICAL OUTCOMES DISPLAY */}
          {outcomes.length > 0 && (
             <div className="bg-green-50 p-6 rounded-lg shadow-sm border border-green-200">
               <h3 className="text-base font-semibold leading-7 text-green-900 flex items-center gap-2 mb-4"><CheckCircle className="w-5 h-5"/> Validated Historical Consultation Information</h3>
               <div className="space-y-4">
                 {outcomes.map(out => (
                   <div key={out.outcome_id} className="bg-white p-4 rounded border border-green-100">
                     <div className="text-sm font-bold text-gray-900 mb-1">Encounter: {out.encounter_id}</div>
                     <div className="text-sm text-gray-700"><strong>Notes:</strong> {out.clinical_notes}</div>
                     {out.follow_up_required && <div className="text-xs text-red-600 font-bold mt-2">Follow-up Required</div>}
                   </div>
                 ))}
               </div>
             </div>
          )}

          {data && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* LEFT COLUMN */}
              <div className="space-y-6">
                
                {/* STEP 4 */}
                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                  <h3 className="text-base font-semibold leading-7 text-gray-900 flex items-center gap-2 border-b pb-2 mb-4"><Calendar className="w-5 h-5 text-gray-400"/> Step 4: Historical Risk</h3>
                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-4xl font-bold tracking-tight text-gray-900">{data.step4.score}</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${data.step4.band === 'HIGH' ? 'bg-red-100 text-red-800' : data.step4.band === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>{data.step4.band} RISK</span>
                  </div>
                  <ul className="mt-4 text-sm text-gray-600 list-disc pl-5 space-y-1">
                    {data.step4.drivers.map((d, i) => <li key={i}>{d}</li>)}
                  </ul>
                  <p className="mt-4 text-xs text-gray-400 font-mono break-all">{data.step4.provenance}</p>
                </div>

                {/* CURRENT CLINICAL INFO */}
                {data.step5?.status === "PENDING" ? (
                  <div className="bg-blue-50 p-6 rounded-lg shadow-sm border border-blue-200">
                    <h3 className="text-base font-semibold leading-7 text-blue-900 flex items-center gap-2 mb-4"><Activity className="w-5 h-5"/> Enter Current Vitals</h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.keys(clinicalForm).map(key => (
                        <div key={key}>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{key}</label>
                          {key === "AVPU" ? (
                            <select value={clinicalForm[key]} onChange={e => setClinicalForm({...clinicalForm, [key]: e.target.value})} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm py-1.5 px-2 border">
                              <option value="">-- Select --</option><option value="A">A (Alert)</option><option value="V">V (Voice)</option><option value="P">P (Pain)</option><option value="U">U (Unresponsive)</option>
                            </select>
                          ) : ["Chest Pain", "Bleeding", "Convulsions", "Allergic Reaction", "Active High-Risk Condition", "Safety Conflict"].includes(key) ? (
                            <select value={clinicalForm[key]} onChange={e => setClinicalForm({...clinicalForm, [key]: e.target.value})} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm py-1.5 px-2 border">
                              <option value="">--</option><option value="Yes">Yes</option><option value="No">No</option>
                            </select>
                          ) : key === "required_specialty_hint" ? (
                             <select value={clinicalForm[key]} onChange={e => setClinicalForm({...clinicalForm, [key]: e.target.value})} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm py-1.5 px-2 border">
                              <option value="">--</option><option value="Cardiology">Cardiology</option><option value="General Practice">General Practice</option>
                            </select>
                          ) : (
                            <input type="text" value={clinicalForm[key]} onChange={e => setClinicalForm({...clinicalForm, [key]: e.target.value})} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm py-1.5 px-2 border" />
                          )}
                        </div>
                      ))}
                    </div>
                    <button onClick={() => fetchPatientData(selectedEncounter.patientId, selectedEncounter.encounterId, true)} disabled={loading} className="mt-6 w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 font-medium">
                      Evaluate Condition
                    </button>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-4 rounded-lg shadow-sm border border-gray-200 text-center text-sm font-medium text-gray-500 flex items-center justify-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-500"/> Current condition submitted.
                  </div>
                )}

                {/* EXPLANATION */}
                {explanation && (
                  <div className="bg-purple-50 p-6 rounded-lg shadow-sm border border-purple-200">
                    <h3 className="text-base font-semibold leading-7 text-purple-900 mb-2">Determininstic Explanation Layer</h3>
                    <div className="text-sm text-purple-800 space-y-2 whitespace-pre-wrap">{explanation}</div>
                  </div>
                )}

              </div>

              {/* RIGHT COLUMN */}
              {data.step6 && (
                <div className="space-y-6">
                  
                  {/* STEP 5 Safety */}
                  <div className={`p-6 rounded-lg shadow-sm border ${data.step5.status === 'RED' ? 'bg-red-50 border-red-200' : data.step5.status === 'YELLOW' ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'}`}>
                    <h3 className={`text-base font-semibold leading-7 flex items-center gap-2 border-b pb-2 mb-4 ${data.step5.status === 'RED' ? 'text-red-900 border-red-200' : data.step5.status === 'YELLOW' ? 'text-yellow-900 border-yellow-200' : 'text-green-900 border-green-200'}`}>
                      Step 5: Safety Gate
                    </h3>
                    <div className="text-2xl font-bold tracking-tight mb-2">{data.step5.status}</div>
                    <p className="text-sm">{data.step5.report}</p>
                    {data.step5.rules.length > 0 && (
                      <ul className="mt-2 text-xs opacity-80 list-disc pl-5">
                        {data.step5.rules.map((r, i) => <li key={i}>{r.rule_id}: {r.reason}</li>)}
                      </ul>
                    )}
                  </div>

                  {/* STEP 6 Pathway */}
                  <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <h3 className="text-base font-semibold leading-7 text-gray-900 flex items-center gap-2 border-b pb-2 mb-4">Step 6: Care Pathway</h3>
                    <div className="text-xl font-bold text-indigo-600 mb-1">{data.step6.Pathway} - {data.step6.Name}</div>
                    <p className="text-sm text-gray-600">{data.step6.Reason}</p>
                  </div>

                  {/* STEP 7 Provider & Action */}
                  <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <h3 className="text-base font-semibold leading-7 text-gray-900 flex items-center gap-2 border-b pb-2 mb-4">Step 7: Provider Matching & Decision</h3>
                    
                    {data.step7?.Status === "BLOCKED" && <div className="p-4 bg-red-100 text-red-800 rounded-md font-medium text-sm">❌ Routine provider matching BLOCKED due to safety status.</div>}
                    
                    {data.step7?.Status === "SUCCESS" && (
                      <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Recommended Options (TOPSIS Ranked)</label>
                        <div className="space-y-3">
                          {data.step7.Options.map((opt, i) => (
                            <div key={i} className="border border-gray-200 rounded p-3 bg-gray-50 flex justify-between items-center">
                              <div>
                                <div className="font-medium text-sm">{opt.Name} <span className="text-xs text-gray-500">({opt.Specialty})</span></div>
                                <div className="text-xs text-gray-500 mt-1">NPI: {opt.NPI} | CCN: {opt.Facilities_CCN?.[0] || 'N/A'}</div>
                              </div>
                              <div className="text-indigo-600 font-bold">{opt.TOPSIS_Score}/100</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {!approved ? (
                      <div className="mt-6 border-t pt-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Clinical Decision Reasoning</label>
                        <textarea value={auditReason} onChange={e => setAuditReason(e.target.value)} className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2 mb-4" rows="3" placeholder="Enter justification..."></textarea>
                        <div className="grid grid-cols-4 gap-2">
                          <button onClick={() => handleDecision("APPROVE")} className="bg-green-600 text-white rounded py-2 text-sm font-medium hover:bg-green-700">Approve</button>
                          <button onClick={() => handleDecision("MODIFY")} className="bg-blue-600 text-white rounded py-2 text-sm font-medium hover:bg-blue-700">Modify</button>
                          <button onClick={() => handleDecision("REJECT")} className="bg-red-600 text-white rounded py-2 text-sm font-medium hover:bg-red-700">Reject</button>
                          <button onClick={() => handleDecision("ESCALATE")} className="bg-yellow-500 text-white rounded py-2 text-sm font-medium hover:bg-yellow-600">Escalate</button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-6 border-t pt-4">
                        <div className="mb-4 text-green-600 font-medium flex items-center gap-2"><CheckCircle className="w-5 h-5"/> Plan Approved & Audited</div>
                        
                        {data.step5.status !== "RED" && data.step7?.Status === "SUCCESS" && (
                          <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
                            <h4 className="text-sm font-medium text-gray-900 mb-3">Schedule Appointment</h4>
                            <div className="flex gap-2 mb-3">
                              <select value={apptForm.selectedProviderIndex} onChange={e => setApptForm({...apptForm, selectedProviderIndex: e.target.value})} className="flex-1 rounded-md border-gray-300 shadow-sm sm:text-sm py-1.5 px-2 border">
                                {data.step7.Options.map((opt, i) => <option key={i} value={i}>{opt.Name}</option>)}
                              </select>
                            </div>
                            <div className="flex gap-2">
                              <input type="date" value={apptForm.date} onChange={e => setApptForm({...apptForm, date: e.target.value})} className="flex-1 rounded-md border-gray-300 shadow-sm sm:text-sm py-1.5 px-2 border"/>
                              <input type="time" value={apptForm.time} onChange={e => setApptForm({...apptForm, time: e.target.value})} className="flex-1 rounded-md border-gray-300 shadow-sm sm:text-sm py-1.5 px-2 border"/>
                              <button onClick={handleScheduleAppt} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700">Book</button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                </div>
              )}
            </div>
          )}
          
          {/* APPOINTMENTS TRACKING SECTION */}
          {appointments.length > 0 && (
            <div className="mt-8 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <h2 className="text-lg font-medium text-gray-900 mb-4 border-b pb-2">APPOINTMENT TRACKING & OUTCOMES</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date/Time</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Provider</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {appointments.map(a => (
                      <tr key={a.appointment_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{a.appointment_date} {a.appointment_time}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{a.provider_name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${a.status === 'Completed' ? 'bg-green-100 text-green-800' : (a.status === 'Cancelled' || a.status === 'No-Show' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800')}`}>
                            {a.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {a.status === 'Scheduled' && (
                            <select onChange={(e) => updateApptStatus(a.appointment_id, e.target.value)} defaultValue="" className="block w-full rounded-md border-gray-300 shadow-sm sm:text-sm py-1.5 px-2 border">
                              <option value="" disabled>Update Status...</option>
                              <option value="Completed">Completed</option>
                              <option value="No-Show">No-Show</option>
                              <option value="Cancelled">Cancelled</option>
                              <option value="Rescheduled">Rescheduled</option>
                            </select>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* POST CONSULTATION MODAL */}
          {activeOutcomeApptId && (
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4 border-b pb-2">Post-Consultation Outcome</h3>
                <p className="text-sm text-gray-500 mb-4">Capture EHR outcome for the completed appointment. This information will update the patient's historical record.</p>
                <textarea 
                  value={outcomeForm.notes} 
                  onChange={(e) => setOutcomeForm({...outcomeForm, notes: e.target.value})}
                  placeholder="Clinical notes and outcomes..."
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-3 mb-4"
                  rows="4"
                />
                <label className="flex items-center gap-2 mb-6 text-sm text-gray-700">
                  <input type="checkbox" checked={outcomeForm.followUp} onChange={(e) => setOutcomeForm({...outcomeForm, followUp: e.target.checked})} className="rounded text-indigo-600 focus:ring-indigo-500"/>
                  Schedule Follow-up Required
                </label>
                <div className="flex justify-end gap-3">
                  <button onClick={() => setActiveOutcomeApptId(null)} className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                  <button onClick={submitOutcome} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">Save Outcome</button>
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
