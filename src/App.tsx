import { useEffect, useState } from 'react'
import type { ChangeEvent, DragEvent, MouseEvent } from 'react'
import './App.css'
import Settings from './Settings'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGear } from '@fortawesome/free-solid-svg-icons'
import UploadCard from './components/UploadCard'
import QueueCard from './components/QueueCard'
import EvaluateModal from './components/EvaluateModal'
import ReviewPanel from './components/ReviewPanel'
import type { AssessmentResult, Question, Upload } from './types'

type View = 'main' | 'settings'

function App() {
  const [currentView, setCurrentView] = useState<View>('main')
  const [modelLabel, setModelLabel] = useState('Loading model...')
  const [modelStatus, setModelStatus] = useState<'idle' | 'ready' | 'error'>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [vendorName, setVendorName] = useState('')
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadMessage, setUploadMessage] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState<Upload[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
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
  const [showWorkflowInfo, setShowWorkflowInfo] = useState(false)
  const [assessmentResults, setAssessmentResults] = useState<AssessmentResult[]>([])

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

  const handleDeleteApplicant = async (applicantId: number, vendor: string) => {
    if (!confirm(`Are you sure you want to delete ${vendor}?`)) {
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
    try {
      setEvaluateExtractError('')
      setEvaluateExtracting(true)

      const dbResponse = await fetch(`http://localhost:8000/applicant-answer/${applicantId}/${qId}`)

      if (dbResponse.ok) {
        const dbData = await dbResponse.json()
        if (dbData.answer && dbData.answer.answer_text) {
          setEvaluateAnswer(dbData.answer.answer_text)
          setEvaluateExtracting(false)
          return
        }
      }

      const formData = new FormData()
      formData.append('applicant_id', String(applicantId))
      formData.append('q_id', qId)

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

        const saveFormData = new FormData()
        saveFormData.append('applicant_id', String(applicantId))
        saveFormData.append('q_id', qId)
        saveFormData.append('answer_text', data.paragraph)
        saveFormData.append('source', 'extracted')

        await fetch('http://localhost:8000/applicant-answer', {
          method: 'POST',
          body: saveFormData,
        })
      } else {
        setEvaluateExtractError('No matching section found in PDF.')
        setEvaluateAnswer('')
      }
    } catch (error) {
      console.error('Failed to fetch/extract answer:', error)
      setEvaluateExtractError('Failed to fetch/extract answer')
    } finally {
      setEvaluateExtracting(false)
    }
  }

  const saveApplicantAnswer = async (applicantId: number, qId: string, answerText: string) => {
    if (!answerText.trim() || !qId) {
      return
    }

    try {
      const formData = new FormData()
      formData.append('applicant_id', String(applicantId))
      formData.append('q_id', qId)
      formData.append('answer_text', answerText)
      formData.append('source', 'manual')

      await fetch('http://localhost:8000/applicant-answer', {
        method: 'POST',
        body: formData,
      })
    } catch (error) {
      console.error('Failed to save answer:', error)
    }
  }

  const handleOpenEvaluate = (vendor: string, applicantId: number) => {
    setEvaluateVendor(vendor)
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

  const loadAssessmentResults = async (applicantId: number) => {
    try {
      const response = await fetch(`http://localhost:8000/assessment-results/${applicantId}`)
      if (response.ok) {
        const data = await response.json()
        setAssessmentResults(data.results || [])
      } else {
        setAssessmentResults([])
      }
    } catch (error) {
      console.error('Failed to load assessment results:', error)
      setAssessmentResults([])
    }
  }

  const handleQuestionChange = (qId: string) => {
    setEvaluateQuestion(qId)
    if (evaluateApplicantId) {
      fetchCriterionAnswer(evaluateApplicantId, qId)
    }
  }

  const handleAnswerBlur = () => {
    if (evaluateApplicantId && evaluateQuestion && evaluateAnswer) {
      saveApplicantAnswer(evaluateApplicantId, evaluateQuestion, evaluateAnswer)
    }
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

      await response.json()
      await loadUploads()
      await loadAssessmentResults(evaluateApplicantId)

      setSelectedApplicantId(evaluateApplicantId)
      setSelectedQuestionId(evaluateQuestion)
      setIsEvaluateOpen(false)
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Evaluation failed')
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
    if (!uploads.length) {
      setSelectedApplicantId(null)
      return
    }
    if (!selectedApplicantId || !uploads.some((upload) => upload.id === selectedApplicantId)) {
      setSelectedApplicantId(uploads[0].id)
    }
  }, [uploads, selectedApplicantId])

  useEffect(() => {
    if (selectedApplicantId) {
      loadAssessmentResults(selectedApplicantId)
    } else {
      setAssessmentResults([])
    }
  }, [selectedApplicantId])

  useEffect(() => {
    if (!assessmentResults.length) {
      setSelectedQuestionId(null)
      return
    }
    if (!selectedQuestionId || !assessmentResults.some((result) => result.q_id === selectedQuestionId)) {
      setSelectedQuestionId(assessmentResults[0].q_id)
    }
  }, [selectedApplicantId, selectedQuestionId, assessmentResults])

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
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

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
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

  const handleUpload = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()

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

      await loadUploads()
    } catch (error) {
      setUploadStatus('error')
      setUploadMessage(error instanceof Error ? error.message : 'Upload failed')
    }
  }

  const handleBrowse = () => {
    document.getElementById('file-input')?.click()
  }

  const selectedApplicant = uploads.find((upload) => upload.id === selectedApplicantId) ?? null

  if (currentView === 'settings') {
    return (
      <div className="app settings-view">
        <div className="nav-bar">
          <button className="link-button" onClick={() => setCurrentView('main')}>
            Back to Main
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

        <UploadCard
          selectedFile={selectedFile}
          vendorName={vendorName}
          uploadStatus={uploadStatus}
          uploadMessage={uploadMessage}
          isDragging={isDragging}
          onFileChange={handleFileChange}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onUpload={handleUpload}
          onVendorChange={setVendorName}
          onBrowse={handleBrowse}
        />

        <QueueCard
          uploads={uploads}
          selectedApplicantId={selectedApplicantId}
          onSelectApplicant={setSelectedApplicantId}
          onEvaluate={handleOpenEvaluate}
          onDelete={handleDeleteApplicant}
        />
      </section>

      {isEvaluateOpen && (
        <EvaluateModal
          vendorName={evaluateVendor}
          questions={questions}
          evaluateQuestion={evaluateQuestion}
          evaluateAnswer={evaluateAnswer}
          evaluateStatus={evaluateStatus}
          evaluateExtracting={evaluateExtracting}
          evaluateExtractError={evaluateExtractError}
          showWorkflowInfo={showWorkflowInfo}
          onToggleWorkflowInfo={() => setShowWorkflowInfo(!showWorkflowInfo)}
          onClose={handleCloseEvaluate}
          onQuestionChange={handleQuestionChange}
          onAnswerChange={setEvaluateAnswer}
          onAnswerBlur={handleAnswerBlur}
          onRunEvaluation={handleRunEvaluation}
        />
      )}

      <ReviewPanel
        selectedApplicant={selectedApplicant}
        assessmentResults={assessmentResults}
        selectedQuestionId={selectedQuestionId}
        onSelectQuestion={(qId) => setSelectedQuestionId(qId)}
      />
    </div>
  )
}

export default App
