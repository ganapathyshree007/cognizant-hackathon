import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { supabase } from './supabase'

import Login from './pages/Login'
import CareManagerDashboard from './pages/CareManagerDashboard'
import PatientDashboard from './pages/PatientDashboard'
import AdminDemoTesting from './pages/AdminDemoTesting'

function App() {
  const [session, setSession] = useState(null)
  const [role, setRole] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) fetchRole(session.user.id)
      else setLoading(false)
    })

    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      if (session) fetchRole(session.user.id)
      else setRole(null)
    })
  }, [])

  const fetchRole = async (userId) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', userId)
      .single()
    
    if (data) setRole(data.role)
    setLoading(false)
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading application...</div>
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 text-gray-900">
        <Routes>
          <Route path="/login" element={!session ? <Login /> : <Navigate to="/" />} />
          
          <Route path="/" element={
            !session ? <Navigate to="/login" /> :
            role === 'CARE_MANAGER' ? <CareManagerDashboard session={session} /> :
            role === 'PATIENT' ? <PatientDashboard session={session} /> :
            <div className="p-8">No assigned role. Please contact administrator.</div>
          } />
          
          <Route path="/admin-demo" element={
            !session ? <Navigate to="/login" /> :
            role === 'CARE_MANAGER' ? <AdminDemoTesting session={session} /> :
            <Navigate to="/" />
          } />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
