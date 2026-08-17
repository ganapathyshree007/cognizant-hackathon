import { useState } from 'react'
import { supabase } from '../supabase'
import { Link } from 'react-router-dom'
import { Database, Link as LinkIcon, Search, AlertCircle, CheckCircle } from 'lucide-react'

export default function AdminDemoTesting({ session }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const [targetProfileEmail, setTargetProfileEmail] = useState('')
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/patients/search?query=${searchQuery}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      })
      if (response.ok) {
        setSearchResults(await response.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleLink = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage(null)
    try {
      // 1. Find profile by email (in a real app, you'd probably search by name or list unlinked patient profiles)
      // Since email is in auth.users, and we only have profiles, we might need a workaround or just list PATIENT roles.
      
      const { data: profiles, error: profileErr } = await supabase
        .from('profiles')
        .select('id, full_name')
        .eq('role', 'PATIENT')
        // if we want to filter by name: .ilike('full_name', `%${targetProfileEmail}%`)
        
      if (profileErr) throw profileErr
      
      const profile = profiles.find(p => p.full_name?.toLowerCase().includes(targetProfileEmail.toLowerCase()))
      if (!profile) throw new Error("No patient profile found matching that name.")

      // 2. Insert into patients table to link EHR patient_id to profile_id
      const { error: insertErr } = await supabase
        .from('patients')
        .insert({
          profile_id: profile.id,
          patient_id: selectedPatientId,
          name: profile.full_name
        })
      
      if (insertErr) {
        if (insertErr.code === '23505') throw new Error("This profile or EHR ID is already linked.")
        throw insertErr
      }
      
      setMessage({ type: 'success', text: `Successfully linked EHR Patient ${selectedPatientId} to Profile ${profile.full_name}` })
      setTargetProfileEmail('')
      setSelectedPatientId('')
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2 text-gray-900"><Database className="w-8 h-8 text-indigo-600"/> Historical EHR Test Data</h1>
          <p className="mt-2 text-gray-500">Select and link existing real patient history to user accounts for demonstration. Do not fabricate records.</p>
        </div>
        <Link to="/" className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50">
          Back to Dashboard
        </Link>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2"><Search className="w-5 h-5"/> Step 1: Find Existing EHR Record</h2>
        <div className="flex gap-4 mb-6">
          <input 
            type="text" 
            placeholder="Search by Patient ID in local DB" 
            className="flex-1 rounded-md border-gray-300 shadow-sm sm:text-sm py-2 px-3 border"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button onClick={handleSearch} className="bg-gray-800 text-white px-6 py-2 rounded-md hover:bg-gray-900 transition">Search</button>
        </div>

        {searchResults.length > 0 && (
          <div className="overflow-x-auto border rounded-md">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patient ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latest Encounter</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {searchResults.map((r, i) => (
                  <tr key={i} className={selectedPatientId === r.PATIENT_ID ? "bg-indigo-50" : ""}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 font-mono">{r.PATIENT_ID}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.ENCOUNTER_ID}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button onClick={() => setSelectedPatientId(r.PATIENT_ID)} className="text-indigo-600 hover:text-indigo-900">
                        {selectedPatientId === r.PATIENT_ID ? "Selected" : "Select"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedPatientId && (
        <div className="bg-indigo-50 p-6 rounded-lg shadow-sm border border-indigo-200">
          <h2 className="text-lg font-medium text-indigo-900 mb-4 flex items-center gap-2"><LinkIcon className="w-5 h-5"/> Step 2: Link to Patient Profile</h2>
          
          {message && (
            <div className={`p-4 rounded-md mb-4 flex items-center gap-2 ${message.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-green-100 text-green-800 border border-green-200'}`}>
              {message.type === 'error' ? <AlertCircle className="w-5 h-5"/> : <CheckCircle className="w-5 h-5"/>}
              {message.text}
            </div>
          )}

          <form onSubmit={handleLink} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-indigo-900 mb-1">Selected EHR Patient ID</label>
              <input type="text" readOnly value={selectedPatientId} className="block w-full rounded-md border-indigo-300 bg-indigo-100 shadow-sm sm:text-sm py-2 px-3 border text-indigo-900 font-mono"/>
            </div>
            <div>
              <label className="block text-sm font-medium text-indigo-900 mb-1">Target Account Name (Must be registered as PATIENT role)</label>
              <input 
                type="text" 
                required
                placeholder="e.g. John Doe"
                value={targetProfileEmail}
                onChange={e => setTargetProfileEmail(e.target.value)} 
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3 border bg-white"
              />
            </div>
            <button type="submit" disabled={loading} className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition font-medium">
              {loading ? "Linking..." : "Confirm Link"}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
