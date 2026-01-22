import { useEffect, useState } from 'react'
import './App.css'
import Settings from './Settings'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGear, faTrash, faWandMagicSparkles } from '@fortawesome/free-solid-svg-icons'

type View = 'main' | 'settings'

function App() {
  const [currentView, setCurrentView] = useState<View>('main')
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
    id: number
    filename: string
    vendor_name: string
    file_size: number
    uploaded_at: number
    status: string
    evaluation_score?: number | null
    evaluation_result?: {
      evaluations?: Record<string, {
        question_text?: string
        answer_text?: string
        parsed_result?: unknown
        llm_response?: string
      }>
      last_updated?: string
    } | null
  }>>([])
  const [questions, setQuestions] = useState<Array<{
    id: number
    q_id: string
    prompt_json: Record<string, unknown>
  }>>([])
  const [isEvaluateOpen, setIsEvaluateOpen] = useState(false)
  const [evaluateVendor, setEvaluateVendor] = useState('')
  const [evaluateApplicantId, setEvaluateApplicantId] = useState<number | null>(null)
  const [evaluateQuestion, setEvaluateQuestion] = useState('')
  const [evaluateAnswer, setEvaluateAnswer] = useState('')
  const [evaluateStatus, setEvaluateStatus] = useState<'idle' | 'loading'>('idle')
  const [evaluateExtracting, setEvaluateExtracting] = useState(false)
  const [evaluateExtractError, setEvaluateExtractError] = useState('')
  const [selectedApplicantId, setSelectedApplicantId] = useState<number | null>(null)
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null)

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

  const loadQuestions = async () => {
    try {
      const response = await fetch('http://localhost:8000/questions')
      if (response.ok) {
        const data = await response.json()
        setQuestions(data.questions || [])
      }
    } catch (error) {
      console.error('Failed to load questions:', error)
    }
  }

  const handleDeleteApplicant = async (applicantId: number, vendorName: string) => {
    if (!confirm(`Are you sure you want to delete ${vendorName}?`)) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/uploads/${applicantId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        await loadUploads()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const fetchCriterionAnswer = async (applicantId: number, qId: string) => {
    const match = qId.match(/\d+/)
    if (!match) {
      return
    }

    const formData = new FormData()
    formData.append('applicant_id', String(applicantId))
    formData.append('criterion_number', match[0])

    try {
      setEvaluateExtractError('')
      setEvaluateExtracting(true)
      const response = await fetch('http://localhost:8000/extract-answer', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        setEvaluateExtractError(error?.detail || 'Failed to extract answer')
        setEvaluateAnswer('')
        return
      }

      const data = await response.json()
      if (data?.paragraph) {
        setEvaluateAnswer(data.paragraph)
      } else {
        setEvaluateExtractError('No paragraph found for this criterion.')
        setEvaluateAnswer('')
      }
    } catch (error) {
      console.error('Failed to extract answer:', error)
      setEvaluateExtractError('Failed to extract answer')
    } finally {
      setEvaluateExtracting(false)
    }
  }

  const handleOpenEvaluate = (vendorNameValue: string, applicantId: number) => {
    setEvaluateVendor(vendorNameValue)
    setEvaluateQuestion('')
    setEvaluateAnswer('')
    setEvaluateApplicantId(applicantId)
    setIsEvaluateOpen(true)
    setEvaluateExtractError('')
  }

  const handleCloseEvaluate = () => {
    if (evaluateStatus === 'loading') {
      return
    }
    setIsEvaluateOpen(false)
  }

  const handleRunEvaluation = async () => {
    if (!evaluateApplicantId || !evaluateQuestion || !evaluateAnswer.trim()) {
      alert('Please select a question and paste the answer.')
      return
    }

    const formData = new FormData()
    formData.append('applicant_id', String(evaluateApplicantId))
    formData.append('q_id', evaluateQuestion)
    formData.append('answer_text', evaluateAnswer.trim())

    try {
      setEvaluateStatus('loading')
      const response = await fetch('http://localhost:8000/evaluate', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Evaluation failed')
      }

      const data = await response.json()
      alert(
        data.parsed_result
          ? JSON.stringify(data.parsed_result, null, 2)
          : data.llm_response,
      )
      await loadUploads()
      setSelectedApplicantId(evaluateApplicantId)
      setIsEvaluateOpen(false)
    } catch (error) {
      alert(
        error instanceof Error
          ? error.message
          : 'Evaluation failed',
      )
    } finally {
      setEvaluateStatus('idle')
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
    loadQuestions()

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (!isEvaluateOpen || !evaluateApplicantId || !evaluateQuestion) {
      return
    }
    fetchCriterionAnswer(evaluateApplicantId, evaluateQuestion)
  }, [isEvaluateOpen, evaluateApplicantId, evaluateQuestion])

  useEffect(() => {
    if (!uploads.length) {
      setSelectedApplicantId(null)
      return
    }
    if (!selectedApplicantId || !uploads.some((upload) => upload.id === selectedApplicantId)) {
      setSelectedApplicantId(uploads[0].id)
    }
  }, [uploads, selectedApplicantId])

  const selectedApplicant = uploads.find((upload) => upload.id === selectedApplicantId) ?? null
  const evaluationMap = selectedApplicant?.evaluation_result?.evaluations ?? {}
  const evaluationIds = Object.keys(evaluationMap)

  useEffect(() => {
    if (!evaluationIds.length) {
      setSelectedQuestionId(null)
      return
    }
    if (!selectedQuestionId || !evaluationMap[selectedQuestionId]) {
      setSelectedQuestionId(evaluationIds[0])
    }
  }, [selectedApplicantId, selectedQuestionId, evaluationIds.join('|')])

  const selectedEvaluation = selectedQuestionId ? evaluationMap[selectedQuestionId] : null
  const parsedResult = selectedEvaluation?.parsed_result
  const parsedObject =
    parsedResult && typeof parsedResult === 'object' && !Array.isArray(parsedResult)
      ? (parsedResult as Record<string, unknown>)
      : null
  const scoreValue = parsedObject?.score
  const scoreLabel =
    typeof scoreValue === 'number' || typeof scoreValue === 'string'
      ? `${scoreValue}`
      : 'N/A'
  const justification =
    parsedObject?.justification ??
    parsedObject?.summary ??
    (typeof parsedResult === 'string' ? parsedResult : '')

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

  if (currentView === 'settings') {
    return (
      <div className="app settings-view">
        <div className="nav-bar">
          <button className="link-button" onClick={() => setCurrentView('main')}>
            ← Back to Main
          </button>
        </div>
        <Settings />
      </div>
    )
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
          <button className="icon-button settings-button" onClick={() => setCurrentView('settings')}>
            <FontAwesomeIcon icon={faGear} />
            <span>Settings</span>
          </button>
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
              uploads.map((upload) => (
                <div className="queue-row" key={upload.id}>
                  <span>{upload.vendor_name} - {upload.filename}</span>
                  <span className="pill success">Uploaded</span>
                  <div className="queue-actions">
                    <button
                      className="secondary ghost"
                      type="button"
                      onClick={() => setSelectedApplicantId(upload.id)}
                    >
                      View Details
                    </button>
                    <button
                      className="icon-button evaluate-button"
                      type="button"
                      onClick={() => handleOpenEvaluate(upload.vendor_name, upload.id)}
                      title="Run LLM assessment"
                    >
                      <FontAwesomeIcon icon={faWandMagicSparkles} />
                    </button>
                    <button
                      className="icon-button delete-button"
                      type="button"
                      onClick={() => handleDeleteApplicant(upload.id, upload.vendor_name)}
                      title="Delete"
                    >
                      <FontAwesomeIcon icon={faTrash} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      {isEvaluateOpen && (
        <div className="modal-overlay" onClick={handleCloseEvaluate}>
          <div
            className="modal-card"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="modal-header">
              <div>
                <p className="eyebrow">LLM Assessment</p>
                <h2>Evaluate {evaluateVendor}</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={handleCloseEvaluate}
                aria-label="Close"
              >
                ×
              </button>
            </header>
            <div className="modal-body">
              <label className="field">
                <span>Question</span>
                <select
                  value={evaluateQuestion}
                  onChange={(event) => {
                    const nextValue = event.target.value
                    setEvaluateQuestion(nextValue)
                    if (evaluateApplicantId) {
                      fetchCriterionAnswer(evaluateApplicantId, nextValue)
                    }
                  }}
                >
                  <option value="" disabled>
                    Select a question
                  </option>
                  {questions.map((question) => {
                    return (
                      <option key={question.q_id} value={question.q_id}>
                        {question.q_id}
                      </option>
                    )
                  })}
                </select>
              </label>
              <label className="field">
                <span>Proposal answer</span>
                <textarea
                  className="modal-textarea"
                  value={evaluateAnswer}
                  onChange={(event) => setEvaluateAnswer(event.target.value)}
                  placeholder="Paste the answer from the proposal"
                  rows={10}
                />
                {evaluateExtracting && (
                  <p className="upload-message uploading">Extracting proposal answer...</p>
                )}
                {evaluateExtractError && (
                  <p className="upload-message error">{evaluateExtractError}</p>
                )}
              </label>
            </div>
            <footer className="modal-footer">
              <button
                className="secondary ghost"
                type="button"
                onClick={handleCloseEvaluate}
                disabled={evaluateStatus === 'loading'}
              >
                Cancel
              </button>
              <button
                className="primary"
                type="button"
                onClick={handleRunEvaluation}
                disabled={evaluateStatus === 'loading'}
              >
                {evaluateStatus === 'loading' ? 'Running...' : 'Run assessment'}
              </button>
            </footer>
          </div>
        </div>
      )}

      <section className="panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Review Application</p>
            <h1>{selectedApplicant ? `${selectedApplicant.vendor_name} Proposal` : 'Select a vendor'}</h1>
          </div>
        </header>

        <div className="review-body">
          <aside className="sidebar">
            <div className="sidebar-card">
              <h3>{selectedApplicant ? `${selectedApplicant.vendor_name} Proposal` : 'No vendor selected'}</h3>
              <div className="status-line">
                <span className={`pill ${selectedApplicant?.status === 'completed' ? 'success' : 'muted'}`}>
                  {selectedApplicant?.status ?? 'Not evaluated'}
                </span>
                <span className="score">
                  Overall Score: {selectedApplicant?.evaluation_score ?? 'N/A'}
                </span>
              </div>
              <button className="secondary" type="button">
                Re-run Evaluation
              </button>
              <button className="secondary" type="button">
                Export JSON
              </button>
            </div>
            <div className="sidebar-list">
              {evaluationIds.length === 0 ? (
                <div className="question">No assessments yet</div>
              ) : (
                evaluationIds.map((questionId) => {
                  const entry = evaluationMap[questionId]
                  const entryParsed = entry?.parsed_result
                  const entryObject =
                    entryParsed && typeof entryParsed === 'object' && !Array.isArray(entryParsed)
                      ? (entryParsed as Record<string, unknown>)
                      : null
                  const entryScore = entryObject?.score
                  const entryScoreLabel =
                    typeof entryScore === 'number' || typeof entryScore === 'string'
                      ? entryScore
                      : 'N/A'

                  return (
                    <button
                      key={questionId}
                      className={`question ${questionId === selectedQuestionId ? 'active' : ''}`}
                      type="button"
                      onClick={() => setSelectedQuestionId(questionId)}
                    >
                      {questionId} <span>{entryScoreLabel}</span>
                    </button>
                  )
                })
              )}
            </div>
          </aside>

          <main className="review-main">
            <div className="card">
              {selectedApplicant ? (
                evaluationIds.length ? (
                  <>
                    <h2>
                      {selectedQuestionId}: <span>{selectedEvaluation?.question_text || 'Question'}</span>
                    </h2>
                    <div className="callout">
                      <h3>Extracted Answer</h3>
                      <p>{selectedEvaluation?.answer_text || 'No answer stored.'}</p>
                    </div>
                    <div className="assessment">
                      <div className="assessment-title">
                        <h3>Assessment & Score</h3>
                        <span className="score-badge">{scoreLabel}</span>
                      </div>
                      {justification ? (
                        <p>{justification}</p>
                      ) : (
                        <p>No justification returned by the model.</p>
                      )}
                      {parsedResult ? (
                        <pre className="json-block">{JSON.stringify(parsedResult, null, 2)}</pre>
                      ) : (
                        <p>No parsed output available.</p>
                      )}
                    </div>
                  </>
                ) : (
                  <p>No assessments stored for this vendor yet.</p>
                )
              ) : (
                <p>Select a vendor from the queue to see assessment results.</p>
              )}
            </div>
          </main>
        </div>
      </section>
    </div>
  )
}

export default App
