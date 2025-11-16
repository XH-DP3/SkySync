import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchMessage()
  }, [])

  const fetchMessage = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/hello')
      const data = await response.json()
      setMessage(data.message)
    } catch (error) {
      console.error('Error fetching message:', error)
      setMessage('Failed to connect to backend')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="App">
      <h1>HackCamp - React + Flask</h1>
      <div className="card">
        {loading ? (
          <p>Loading...</p>
        ) : (
          <p>{message || 'Click the button to fetch from backend'}</p>
        )}
        <button onClick={fetchMessage} disabled={loading}>
          Fetch from Backend
        </button>
      </div>
    </div>
  )
}

export default App

