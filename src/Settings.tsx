import { useEffect, useState } from 'react'
import './App.css'

interface Question {
  id: number
  q_id: string
  prompt_json: {
    question: string
    scale: string
    required_evidence: string[]
    evaluation_guidance: string[]
    output_format: Record<string, string>
  }
  is_active: boolean
}

function Settings() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [newQId, setNewQId] = useState('')
  const [jsonText, setJsonText] = useState('')
  const [message, setMessage] = useState<{text: string, type: 'success' | 'error'} | null>(null)

  const loadQuestions = async () => {
    try {
      const response = await fetch('http://localhost:8000/questions')
      if (response.ok) {
        const data = await response.json()
        setQuestions(data.questions)
      }
    } catch (error) {
      console.error('Failed to load questions:', error)
    }
  }

  useEffect(() => {
    loadQuestions()
  }, [])

  const handleEdit = (question: Question) => {
    setEditingQuestion(question)
    setJsonText(JSON.stringify(question.prompt_json, null, 2))
    setIsCreating(false)
  }

  const handleCreate = () => {
    setIsCreating(true)
    setEditingQuestion(null)
    setNewQId('')
    setJsonText(JSON.stringify({
      question: "",
      scale: "0-5",
      required_evidence: [],
      evaluation_guidance: [],
      output_format: {
        score: "integer 0-5",
        justification: "brief explanation"
      }
    }, null, 2))
  }

  const handleCancel = () => {
    setEditingQuestion(null)
    setIsCreating(false)
    setJsonText('')
    setNewQId('')
    setMessage(null)
  }

  const handleSave = async () => {
    try {
      // Validate JSON
      JSON.parse(jsonText)
    } catch (e) {
      setMessage({text: 'Invalid JSON format', type: 'error'})
      return
    }

    const formData = new FormData()
    formData.append('prompt_json', jsonText)
    formData.append('is_active', 'true')

    try {
      let response
      if (isCreating) {
        if (!newQId.trim()) {
          setMessage({text: 'Question ID is required', type: 'error'})
          return
        }
        formData.append('q_id', newQId.trim())
        response = await fetch('http://localhost:8000/questions', {
          method: 'POST',
          body: formData,
        })
      } else if (editingQuestion) {
        response = await fetch(`http://localhost:8000/questions/${editingQuestion.q_id}`, {
          method: 'PUT',
          body: formData,
        })
      }

      if (response && response.ok) {
        setMessage({text: isCreating ? 'Question created successfully' : 'Question updated successfully', type: 'success'})
        await loadQuestions()
        setTimeout(() => {
          handleCancel()
        }, 1500)
      } else {
        const error = await response?.json()
        setMessage({text: error?.detail || 'Failed to save question', type: 'error'})
      }
    } catch (error) {
      setMessage({text: error instanceof Error ? error.message : 'Failed to save question', type: 'error'})
    }
  }

  const handleDelete = async (q_id: string) => {
    if (!confirm(`Are you sure you want to delete question ${q_id}?`)) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/questions/${q_id}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setMessage({text: 'Question deleted successfully', type: 'success'})
        await loadQuestions()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({text: error?.detail || 'Failed to delete question', type: 'error'})
      }
    } catch (error) {
      setMessage({text: error instanceof Error ? error.message : 'Failed to delete question', type: 'error'})
    }
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1>Evaluation Questions Settings</h1>
        <button className="primary" onClick={handleCreate}>
          Create New Question
        </button>
      </div>

      {message && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      {(editingQuestion || isCreating) && (
        <div className="card editor-card">
          <h2>{isCreating ? 'Create New Question' : `Edit Question ${editingQuestion?.q_id}`}</h2>
          {isCreating && (
            <label className="field">
              <span>Question ID</span>
              <input
                placeholder="e.g., Q2, Q3"
                value={newQId}
                onChange={(e) => setNewQId(e.target.value)}
              />
            </label>
          )}
          <label className="field">
            <span>Prompt JSON</span>
            <textarea
              className="json-editor"
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              rows={20}
            />
          </label>
          <div className="button-group">
            <button className="primary" onClick={handleSave}>
              Save
            </button>
            <button className="secondary" onClick={handleCancel}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="card questions-list">
        <h2>Current Questions</h2>
        {questions.length === 0 ? (
          <p>No questions found. Create one to get started.</p>
        ) : (
          <div className="questions-grid">
            {questions.map((q) => (
              <div className="question-item" key={q.id}>
                <div className="question-header">
                  <h3>{q.q_id}</h3>
                  <span className={`pill ${q.is_active ? 'success' : 'secondary'}`}>
                    {q.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="question-text">{q.prompt_json.question}</p>
                <div className="question-meta">
                  <span>Scale: {q.prompt_json.scale}</span>
                  <span>Evidence items: {q.prompt_json.required_evidence?.length || 0}</span>
                </div>
                <div className="button-group">
                  <button className="secondary" onClick={() => handleEdit(q)}>
                    Edit
                  </button>
                  <button className="secondary ghost" onClick={() => handleDelete(q.q_id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings
