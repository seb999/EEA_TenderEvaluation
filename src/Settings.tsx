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
  search_label: string
  auto_increment: boolean
}

interface SearchKeyword {
  id: number
  keyword: string
  is_active: boolean
  created_at: string
}

function Settings() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [newQId, setNewQId] = useState('')
  const [jsonText, setJsonText] = useState('')
  const [searchLabel, setSearchLabel] = useState('Criterion')
  const [autoIncrement, setAutoIncrement] = useState(true)
  const [message, setMessage] = useState<{text: string, type: 'success' | 'error'} | null>(null)

  const [keywords, setKeywords] = useState<SearchKeyword[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [editingKeywordId, setEditingKeywordId] = useState<number | null>(null)
  const [editingKeywordText, setEditingKeywordText] = useState('')

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

  const loadKeywords = async () => {
    try {
      const response = await fetch('http://localhost:8000/search-keywords')
      if (response.ok) {
        const data = await response.json()
        setKeywords(data.keywords)
      }
    } catch (error) {
      console.error('Failed to load keywords:', error)
    }
  }

  useEffect(() => {
    loadQuestions()
    loadKeywords()
  }, [])

  const handleEdit = (question: Question) => {
    setEditingQuestion(question)
    setJsonText(JSON.stringify(question.prompt_json, null, 2))
    setSearchLabel(question.search_label || 'Criterion')
    setAutoIncrement(question.auto_increment !== undefined ? question.auto_increment : true)
    setIsCreating(false)
  }

  const handleCreate = () => {
    setIsCreating(true)
    setEditingQuestion(null)
    setNewQId('')
    setSearchLabel('Criterion')
    setAutoIncrement(true)
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
    setSearchLabel('Criterion')
    setAutoIncrement(true)
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
    formData.append('search_label', searchLabel.trim() || 'Criterion')
    formData.append('auto_increment', String(autoIncrement))

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

  const handleCreateKeyword = async () => {
    if (!newKeyword.trim()) {
      setMessage({text: 'Keyword cannot be empty', type: 'error'})
      return
    }

    const formData = new FormData()
    formData.append('keyword', newKeyword.trim())
    formData.append('is_active', 'true')

    try {
      const response = await fetch('http://localhost:8000/search-keywords', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        setMessage({text: 'Keyword created successfully', type: 'success'})
        setNewKeyword('')
        await loadKeywords()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({text: error?.detail || 'Failed to create keyword', type: 'error'})
      }
    } catch (error) {
      setMessage({text: error instanceof Error ? error.message : 'Failed to create keyword', type: 'error'})
    }
  }

  const handleUpdateKeyword = async (id: number) => {
    if (!editingKeywordText.trim()) {
      setMessage({text: 'Keyword cannot be empty', type: 'error'})
      return
    }

    const formData = new FormData()
    formData.append('keyword', editingKeywordText.trim())
    formData.append('is_active', 'true')

    try {
      const response = await fetch(`http://localhost:8000/search-keywords/${id}`, {
        method: 'PUT',
        body: formData,
      })

      if (response.ok) {
        setMessage({text: 'Keyword updated successfully', type: 'success'})
        setEditingKeywordId(null)
        setEditingKeywordText('')
        await loadKeywords()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({text: error?.detail || 'Failed to update keyword', type: 'error'})
      }
    } catch (error) {
      setMessage({text: error instanceof Error ? error.message : 'Failed to update keyword', type: 'error'})
    }
  }

  const handleDeleteKeyword = async (id: number, keyword: string) => {
    if (!confirm(`Are you sure you want to delete keyword "${keyword}"?`)) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/search-keywords/${id}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setMessage({text: 'Keyword deleted successfully', type: 'success'})
        await loadKeywords()
        setTimeout(() => setMessage(null), 3000)
      } else {
        const error = await response.json()
        setMessage({text: error?.detail || 'Failed to delete keyword', type: 'error'})
      }
    } catch (error) {
      setMessage({text: error instanceof Error ? error.message : 'Failed to delete keyword', type: 'error'})
    }
  }

  const handleEditKeyword = (keyword: SearchKeyword) => {
    setEditingKeywordId(keyword.id)
    setEditingKeywordText(keyword.keyword)
  }

  const handleCancelEditKeyword = () => {
    setEditingKeywordId(null)
    setEditingKeywordText('')
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
            <span>PDF Search Label</span>
            <input
              placeholder="e.g., Criterion, Section, Award Criterion"
              value={searchLabel}
              onChange={(e) => setSearchLabel(e.target.value)}
            />
            <small style={{ color: 'var(--muted)', marginTop: '0.25rem' }}>
              The keyword to search for in PDF files
            </small>
          </label>
          <label className="field" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={autoIncrement}
              onChange={(e) => setAutoIncrement(e.target.checked)}
            />
            <span>Auto-increment with question number</span>
            <small style={{ color: 'var(--muted)', marginLeft: '0.5rem' }}>
              {autoIncrement
                ? `Will search for "${searchLabel} ${newQId.match(/\d+/)?.[0] || editingQuestion?.q_id.match(/\d+/)?.[0] || 'X'}" or "${newQId.match(/\d+/)?.[0] || editingQuestion?.q_id.match(/\d+/)?.[0] || 'X'}. ${searchLabel}" in PDF`
                : `Will search for exact text "${searchLabel}"`}
            </small>
          </label>
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
                  <h3>Question {q.q_id}</h3>
                  <span className={`pill ${q.is_active ? 'success' : 'secondary'}`}>
                    {q.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="question-text">{q.prompt_json.question}</p>
                <div className="question-meta">
                  <span>Scale: {q.prompt_json.scale}</span>
                  <span>Evidence items: {q.prompt_json.required_evidence?.length || 0}</span>
                </div>
                <div className="question-meta">
                  <span className="question-search-label">
                    <strong>PDF Search Label:</strong> {q.search_label || 'Any'}
                  </span>
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

      <div className="card">
        <h2>PDF Search Keywords</h2>
        <p style={{ marginBottom: '1rem', color: 'var(--muted)' }}>
          Configure keywords used to search for sections in PDF files. The system will look for these keywords followed by a number (e.g., "Criterion 2").
        </p>

        <div style={{ marginBottom: '1.5rem' }}>
          <label className="field">
            <span>Add New Keyword</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                placeholder="e.g., Criterion, Section, Award Criterion"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateKeyword()
                  }
                }}
              />
              <button className="primary" onClick={handleCreateKeyword}>
                Add
              </button>
            </div>
          </label>
        </div>

        {keywords.length === 0 ? (
          <p>No keywords configured. The system will use default keywords: "Criterion", "Award Criterion".</p>
        ) : (
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {keywords.map((keyword) => (
              <div
                key={keyword.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem',
                  background: 'var(--soft)',
                  borderRadius: '8px',
                }}
              >
                {editingKeywordId === keyword.id ? (
                  <>
                    <input
                      value={editingKeywordText}
                      onChange={(e) => setEditingKeywordText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleUpdateKeyword(keyword.id)
                        } else if (e.key === 'Escape') {
                          handleCancelEditKeyword()
                        }
                      }}
                      style={{ flex: 1, marginRight: '0.5rem' }}
                      autoFocus
                    />
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="secondary"
                        onClick={() => handleUpdateKeyword(keyword.id)}
                      >
                        Save
                      </button>
                      <button
                        className="secondary ghost"
                        onClick={handleCancelEditKeyword}
                      >
                        Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span style={{ fontWeight: 500 }}>{keyword.keyword}</span>
                      <span className={`pill ${keyword.is_active ? 'success' : 'secondary'}`}>
                        {keyword.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="secondary"
                        onClick={() => handleEditKeyword(keyword)}
                      >
                        Edit
                      </button>
                      <button
                        className="secondary ghost"
                        onClick={() => handleDeleteKeyword(keyword.id, keyword.keyword)}
                      >
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings
