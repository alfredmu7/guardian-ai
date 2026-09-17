import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [lastUpdated, setLastUpdated] = useState(null)
  const streamUrl = '/api/v1/video-feed'

  useEffect(() => {
    let mounted = true

    fetch('/api/v1/health')
      .then((response) => {
        if (!response.ok) throw new Error('Backend unavailable')
        return response.json()
      })
      .then(() => {
        if (mounted) {
          setBackendStatus('online')
          setLastUpdated(new Date())
        }
      })
      .catch(() => {
        if (mounted) setBackendStatus('offline')
      })

    return () => {
      mounted = false
    }
  }, [])

  const statusLabel = {
    checking: 'Comprobando backend',
    online: 'Backend conectado',
    offline: 'Backend sin respuesta',
  }[backendStatus]

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">GUARDIAN AI / LOCAL CONTROL</p>
          <h1>Monitor de presencia</h1>
        </div>
        <div className={`status status-${backendStatus}`}>
          <span className="status-dot" />
          {statusLabel}
        </div>
      </header>

      <section className="dashboard-grid">
        <div className="video-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">CAMARA 01</p>
              <h2>Vista en vivo</h2>
            </div>
            <span className="live-badge">EN DIRECTO</span>
          </div>
          <div className="video-frame">
            <img
              src={streamUrl}
              alt="Video en vivo de la camara ESP32"
              onLoad={() => setLastUpdated(new Date())}
            />
            {backendStatus === 'offline' && (
              <div className="video-message">Esperando conexion con FastAPI</div>
            )}
          </div>
          <div className="panel-footer">
            <span>Fuente: ESP32-CAM por WebSocket</span>
            <span>{lastUpdated ? 'Feed activo' : 'Esperando frames'}</span>
          </div>
        </div>

        <aside className="info-panel">
          <p className="eyebrow">ESTADO DEL SISTEMA</p>
          <div className="metric">
            <span>API local</span>
            <strong>{backendStatus === 'online' ? 'Operativa' : 'Pendiente'}</strong>
          </div>
          <div className="metric">
            <span>Procesamiento</span>
            <strong>YOLOv8 Pose</strong>
          </div>
          <div className="metric">
            <span>Salida</span>
            <strong>MJPEG / 30 ms</strong>
          </div>
          <p className="hint">
            La imagen aparecera cuando la ESP32 este conectada al WebSocket del backend.
          </p>
        </aside>
      </section>
    </main>
  )
}

export default App
