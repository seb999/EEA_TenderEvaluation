import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [modelLabel, setModelLabel] = useState('Loading model...')
  const [modelStatus, setModelStatus] = useState<'idle' | 'ready' | 'error'>(
    'idle',
  )
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [vendorName, setVendorName] = useState('')
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadMessage, setUploadMessage] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState<Array<{
    filename: string
    vendor_name: string
    file_size: number
    uploaded_at: number
    status: string
  }>>([])

  const loadUploads = async () => {
    try {
      const response = await fetch('http://localhost:8000/uploads')
      if (response.ok) {
        const data = await response.json()
        setUploads(data.uploads)
      }
    } catch (error) {
      console.error('Failed to load uploads:', error)
    }
  }

  useEffect(() => {
    let isMounted = true

    const loadModel = async () => {
      try {
        const response = await fetch('http://localhost:8000/model')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        const label =
          typeof data === 'string'
            ? data
            : data?.model ?? data?.name ?? data?.id ?? 'Unknown model'

        if (isMounted) {
          setModelLabel(label)
          setModelStatus('ready')
        }
      } catch (error) {
        if (isMounted) {
          setModelLabel('Model unavailable')
          setModelStatus('error')
        }
      }
    }

    loadModel()
    loadUploads()

    return () => {
      isMounted = false
    }
  }, [])

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
      setUploadMessage('')
      setUploadStatus('idle')
    } else if (file) {
      setUploadMessage('Please select a PDF file')
      setSelectedFile(null)
    }
  }

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)

    const file = event.dataTransfer.files?.[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
      setUploadMessage('')
      setUploadStatus('idle')
    } else if (file) {
      setUploadMessage('Please select a PDF file')
      setSelectedFile(null)
    }
  }

  const handleUpload = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()

    // Prevent multiple uploads
    if (uploadStatus === 'uploading') {
      return
    }

    if (!selectedFile || !vendorName.trim()) {
      setUploadMessage('Please select a file and enter vendor name')
      setUploadStatus('error')
      return
    }

    setUploadStatus('uploading')
    setUploadMessage('Uploading...')

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('vendor_name', vendorName.trim())

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const data = await response.json()
      setUploadStatus('success')
      setUploadMessage(`File uploaded successfully: ${data.filename}`)
      setSelectedFile(null)
      setVendorName('')

      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''

      // Refresh the uploads list
      await loadUploads()
    } catch (error) {
      setUploadStatus('error')
      setUploadMessage(error instanceof Error ? error.message : 'Upload failed')
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="app">
      <section className="panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Tender Evaluator</p>
            <h1>Tender Evaluator</h1>
            <p className={`model-meta ${modelStatus}`}>
              LLM: <span>{modelLabel}</span>
            </p>
          </div>
        </header>

        <div className="card upload-card">
          <h2>Upload New Application</h2>
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div>
              <p>{selectedFile ? selectedFile.name : 'Drag & drop your PDF file here'}</p>
              <input
                id="file-input"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <button
                className="link-button"
                type="button"
                onClick={() => document.getElementById('file-input')?.click()}
              >
                Browse
              </button>
            </div>
          </div>
          <label className="field">
            <span>Applicant Name</span>
            <input
              placeholder="Vendor name"
              value={vendorName}
              onChange={(e) => setVendorName(e.target.value)}
            />
          </label>
          {uploadMessage && (
            <p className={`upload-message ${uploadStatus}`}>{uploadMessage}</p>
          )}
          <button
            className="primary"
            onClick={handleUpload}
            disabled={uploadStatus === 'uploading'}
          >
            {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload & Process'}
          </button>
        </div>

        <div className="card queue-card">
          <h2>Processing Queue</h2>
          <div className="queue-table">
            <div className="queue-row queue-head">
              <span>Applicant / File</span>
              <span>Status</span>
              <span>Actions</span>
            </div>
            {uploads.length === 0 ? (
              <div className="queue-empty">
                <p>No files uploaded yet</p>
              </div>
            ) : (
              uploads.map((upload, index) => (
                <div className="queue-row" key={index}>
                  <span>{upload.vendor_name} - {upload.filename}</span>
                  <span className="pill success">Uploaded</span>
                  <button className="secondary ghost" type="button">
                    View Details
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Review Application</p>
            <h1>Vendor A Proposal</h1>
          </div>
        </header>

        <div className="review-body">
          <aside className="sidebar">
            <div className="sidebar-card">
              <h3>Vendor A Proposal</h3>
              <div className="status-line">
                <span className="pill success">Completed</span>
                <span className="score">Overall Score: 78 / 100</span>
              </div>
              <button className="secondary" type="button">
                Re-run Evaluation
              </button>
              <button className="secondary" type="button">
                Export JSON
              </button>
            </div>
            <div className="sidebar-list">
              <button className="question active" type="button">
                Question 2 <span>4 / 5</span>
              </button>
              <button className="question" type="button">
                Question 3 <span>3 / 5</span>
              </button>
              <button className="question" type="button">
                Question 4 <span>2 / 5</span>
              </button>
            </div>
          </aside>

          <main className="review-main">
            <div className="card">
              <h2>
                Question 2: <span>Describe your approach to data security</span>
              </h2>
              <div className="callout">
                <h3>Extracted Answer</h3>
                <ul>
                  <li>
                    Multi-factor authentication (MFA) for admin access.{' '}
                    <span>(p12 P3)</span>
                  </li>
                  <li>
                    AES-256 encryption for data at rest. <span>(p14 P1)</span>
                  </li>
                  <li>
                    Incident response plan with 24/7 monitoring. <span>(p15 P2)</span>
                  </li>
                </ul>
              </div>
              <div className="assessment">
                <div className="assessment-title">
                  <h3>Assessment & Score</h3>
                  <span className="score-badge">4 / 5</span>
                </div>
                <p>
                  Strong security controls are in place, including MFA and data
                  encryption. 24/7 incident response noted.
                </p>
                <div className="split">
                  <div>
                    <h4>Missing</h4>
                    <ul>
                      <li>Lack of audit process mentioned.</li>
                    </ul>
                  </div>
                  <div>
                    <h4>Follow-ups</h4>
                    <ul>
                      <li>Provide details on audit procedures.</li>
                      <li>Clarify SIEM integration plans.</li>
                    </ul>
                  </div>
                </div>
                <button className="link-button inline" type="button">
                  View JSON Output
                </button>
              </div>
            </div>
          </main>
        </div>
      </section>
    </div>
  )
}

export default App
