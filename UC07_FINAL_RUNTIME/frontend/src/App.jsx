import { useState } from 'react'
import './App.css'

function App() {
  const [patientId, setPatientId] = useState("a1b2c3d4-e5f6-7890-1234-567890abcdef") // example synthea UUID
  const [encounterId, setEncounterId] = useState("b2c3d4e5-f6a7-8901-2345-67890abcdef1")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [auditReason, setAuditReason] = useState("")

  const fetchPatientData = async () => {
    setLoading(true)
    setError(null)
    setData(null)
    
    try {
      const response = await fetch('http://localhost:8000/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          encounter_id: encounterId,
          clinical_context: { "DESCRIPTION": "normal vitals" } // Mocked for UI test
        })
      })
      
      const result = await response.json()
      if (result.error) {
        setError(result)
      } else {
        setData(result)
      }
    } catch (e) {
      setError({ message: e.message, error: "CONNECTION_ERROR" })
    }
    setLoading(false)
  }

  const handleDecision = async (action) => {
    if ((action === "REJECT" || action === "ESCALATE") && !auditReason) {
      alert(`A reason is required to ${action}.`)
      return
    }
    
    try {
      const response = await fetch('http://localhost:8000/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          encounter_id: encounterId,
          reviewer_id: "CM_UI_USER",
          action: action,
          reason: auditReason || "Approved",
          system_pathway: data.step6.Pathway,
          system_provider: data.step7.Options?.[0]?.Name || "NONE",
          selected_provider: data.step7.Options?.[0]?.Name || "NONE"
        })
      })
      
      if (response.ok) {
        alert(`Decision ${action} recorded to Audit Trail!`)
        setAuditReason("")
      }
    } catch (e) {
      alert("Error saving audit trail.")
    }
  }

  return (
    <div className="dashboard-container" style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ borderBottom: '2px solid #ccc', paddingBottom: '10px', marginBottom: '20px' }}>
        <h1>PATIENT CARE MANAGER DASHBOARD</h1>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <input 
            value={patientId} 
            onChange={e => setPatientId(e.target.value)} 
            placeholder="Patient ID"
            style={{ padding: '8px', fontSize: '16px', minWidth: '300px' }}
          />
          <input 
            value={encounterId} 
            onChange={e => setEncounterId(e.target.value)} 
            placeholder="Encounter ID"
            style={{ padding: '8px', fontSize: '16px', minWidth: '300px' }}
          />
          <button onClick={fetchPatientData} disabled={loading} style={{ padding: '8px 16px', fontSize: '16px', cursor: 'pointer' }}>
            {loading ? "Loading..." : "Evaluate Patient"}
          </button>
        </div>
      </header>

      {error && (
        <div style={{ backgroundColor: '#fee', border: '1px solid #f00', padding: '15px', borderRadius: '4px' }}>
          <h2 style={{ color: '#c00', margin: 0 }}>ERROR: {error.error}</h2>
          <p>{error.message}</p>
        </div>
      )}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          
          {/* Left Column */}
          <div>
            {/* Risk Panel */}
            <div style={{ border: '1px solid #ccc', padding: '15px', marginBottom: '20px', borderRadius: '4px' }}>
              <h2 style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginTop: 0 }}>HISTORICAL RISK</h2>
              <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                Risk Score: {data.step4.score} <br/>
                Risk Band: <span style={{ color: data.step4.band === 'HIGH' ? 'red' : 'inherit' }}>{data.step4.band}</span>
              </div>
              <p style={{ fontStyle: 'italic', color: '#666', fontSize: '12px' }}>{data.step4.provenance}</p>
              <h4>Top Risk Drivers:</h4>
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                {data.step4.drivers.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </div>

            {/* Safety Panel */}
            <div style={{ 
              border: '2px solid', 
              borderColor: data.step5.status === 'RED' ? '#f00' : (data.step5.status === 'YELLOW' ? '#fa0' : '#0a0'),
              backgroundColor: data.step5.status === 'RED' ? '#fee' : (data.step5.status === 'YELLOW' ? '#fffaee' : '#efe'),
              padding: '15px', marginBottom: '20px', borderRadius: '4px' 
            }}>
              <h2 style={{ borderBottom: '1px solid #ccc', paddingBottom: '10px', marginTop: 0 }}>CURRENT SAFETY</h2>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                Status: {data.step5.status}
              </div>
              <p><strong>Report:</strong> {data.step5.report}</p>
              {data.step5.rules.length > 0 && (
                <div>
                  <h4>Triggered Rules:</h4>
                  <ul>
                    {data.step5.rules.map((r, i) => <li key={i}>{r.rule_id} - {r.reason}</li>)}
                  </ul>
                </div>
              )}
            </div>
            
            {/* Pathway Panel */}
            <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '4px' }}>
              <h2 style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginTop: 0 }}>CARE PATHWAY</h2>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#0066cc' }}>
                {data.step6.Pathway} - {data.step6.Name}
              </div>
              <p><strong>Reason:</strong> {data.step6.Reason}</p>
            </div>
          </div>

          {/* Right Column */}
          <div>
            {/* Providers Panel */}
            <div style={{ border: '1px solid #ccc', padding: '15px', marginBottom: '20px', borderRadius: '4px' }}>
              <h2 style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginTop: 0 }}>PROVIDER RECOMMENDATIONS</h2>
              
              {data.step7.Status === "BLOCKED" && (
                <div style={{ color: 'red', fontWeight: 'bold', padding: '20px 0' }}>
                  ❌ Normal Provider Matching Blocked due to Safety Status
                </div>
              )}
              
              {data.step7.Status === "CONDITIONAL" && (
                <div style={{ color: '#d97706', fontWeight: 'bold', padding: '20px 0' }}>
                  ⚠️ Conditional: Clinician Clearance Required Before Matching
                </div>
              )}
              
              {data.step7.Status === "NO_MATCH" && (
                <div style={{ color: 'red', fontWeight: 'bold', padding: '20px 0' }}>
                  ❌ NO_PROVIDER_MATCH: {data.step7.Reason}
                </div>
              )}

              {data.step7.Status === "SUCCESS" && (
                <div>
                  <div style={{ backgroundColor: '#f8f9fa', padding: '10px', fontSize: '12px', marginBottom: '15px' }}>
                    <strong>Notice:</strong> Real-time appointment availability and Insurance/network compatibility are not available.
                  </div>
                  {data.step7.Options.map((opt, i) => (
                    <div key={i} style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '10px' }}>
                      <div style={{ fontWeight: 'bold', fontSize: '16px' }}>{i+1}. {opt.Name} <span style={{ float: 'right', color: '#0066cc' }}>{opt.Final_Score} / 100</span></div>
                      <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>{opt.Provenance}</div>
                      <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>Breakdown: {opt.Breakdown}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Decision Panel */}
            <div style={{ border: '2px solid #000', padding: '15px', borderRadius: '4px', backgroundColor: '#f8f9fa' }}>
              <h2 style={{ borderBottom: '1px solid #ccc', paddingBottom: '10px', marginTop: 0 }}>CARE MANAGER DECISION</h2>
              
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>Decision Reason (Required for Reject/Escalate):</label>
                <textarea 
                  value={auditReason}
                  onChange={e => setAuditReason(e.target.value)}
                  style={{ width: '100%', height: '80px', padding: '8px' }}
                  placeholder="Enter clinical justification..."
                />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button onClick={() => handleDecision("APPROVE")} style={{ backgroundColor: '#28a745', color: 'white', padding: '10px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>APPROVE</button>
                <button onClick={() => handleDecision("MODIFY")} style={{ backgroundColor: '#007bff', color: 'white', padding: '10px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>MODIFY</button>
                <button onClick={() => handleDecision("REJECT")} style={{ backgroundColor: '#dc3545', color: 'white', padding: '10px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>REJECT</button>
                <button onClick={() => handleDecision("ESCALATE")} style={{ backgroundColor: '#ffc107', color: 'black', padding: '10px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>ESCALATE</button>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default App
