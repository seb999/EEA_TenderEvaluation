import type { ChangeEvent } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faInfoCircle } from '@fortawesome/free-solid-svg-icons'
import type { Question } from '../types'

type EvaluateModalProps = {
  vendorName: string
  questions: Question[]
  evaluateQuestion: string
  evaluateAnswer: string
  evaluateImage: File | null
  evaluateStatus: 'idle' | 'loading'
  evaluateExtracting: boolean
  evaluateExtractError: string
  supportsImages: boolean
  showWorkflowInfo: boolean
  onToggleWorkflowInfo: () => void
  onClose: () => void
  onQuestionChange: (value: string) => void
  onAnswerChange: (value: string) => void
  onAnswerBlur: () => void
  onImageChange: (file: File | null) => void
  onRunEvaluation: () => void
  onAutoExtract: () => void
}

function EvaluateModal({
  vendorName,
  questions,
  evaluateQuestion,
  evaluateAnswer,
  evaluateImage,
  evaluateStatus,
  evaluateExtracting,
  evaluateExtractError,
  supportsImages,
  showWorkflowInfo,
  onToggleWorkflowInfo,
  onClose,
  onQuestionChange,
  onAnswerChange,
  onAnswerBlur,
  onImageChange,
  onRunEvaluation,
  onAutoExtract,
}: EvaluateModalProps) {
  const selectedQuestion = questions.find((q) => q.q_id === evaluateQuestion)
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <div>
            <p className="eyebrow">LLM Assessment</p>
            <h2>Evaluate {vendorName}</h2>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="icon-button"
              type="button"
              onClick={onToggleWorkflowInfo}
              aria-label="Workflow Info"
              title="Show workflow information"
            >
              <FontAwesomeIcon icon={faInfoCircle} />
            </button>
            <button className="icon-button" type="button" onClick={onClose} aria-label="Close">
              X
            </button>
          </div>
        </header>
        <div className="modal-body">
          {showWorkflowInfo && (
            <div
              style={{
                backgroundColor: '#f0f7ff',
                border: '1px solid #0066cc',
                borderRadius: '6px',
                padding: '16px',
                marginBottom: '16px',
              }}
            >
              <h3
                style={{
                  marginTop: 0,
                  marginBottom: '12px',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#0066cc',
                }}
              >
                Answer Workflow
              </h3>
              <ol style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6' }}>
                <li>
                  <strong>Select a question:</strong> The system checks if an answer has already been stored and loads it automatically.
                </li>
                <li>
                  <strong>Auto-extraction:</strong> Click "Auto Extract" to extract the relevant section from the PDF.
                </li>
                <li>
                  <strong>Manual input:</strong> You can also paste or type an answer directly. It saves when you leave the field.
                </li>
                <li>
                  <strong>Persistence:</strong> Saved answers load instantly on future visits.
                </li>
              </ol>
            </div>
          )}
          <label className="field">
            <span>Question</span>
            <select value={evaluateQuestion} onChange={(event) => onQuestionChange(event.target.value)}>
              <option value="" disabled>
                Select a question
              </option>
              {questions.map((question) => (
                <option key={question.q_id} value={question.q_id}>
                  {question.q_id}
                </option>
              ))}
            </select>
          </label>
          {selectedQuestion && (
            <div
              style={{
                backgroundColor: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '6px',
                padding: '12px',
                marginBottom: '16px',
              }}
            >
              <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 500, color: '#212529' }}>
                {selectedQuestion.prompt_json.question}
              </p>
              <p style={{ margin: 0, fontSize: '13px', color: '#6c757d' }}>
                <strong>Scale:</strong> {selectedQuestion.prompt_json.scale}
              </p>
            </div>
          )}
          <label className="field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span>Proposal answer</span>
              {evaluateQuestion && !evaluateExtracting && (
                <button
                  className="secondary"
                  type="button"
                  onClick={onAutoExtract}
                  style={{ padding: '4px 12px', fontSize: '13px' }}
                >
                  Auto Extract
                </button>
              )}
            </div>
            <textarea
              className="modal-textarea"
              value={evaluateAnswer}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) => onAnswerChange(event.target.value)}
              onBlur={onAnswerBlur}
              placeholder="Paste the answer from the proposal or click 'Auto Extract'"
              rows={10}
            />
            {evaluateExtracting && <p className="upload-message uploading">Extracting proposal answer...</p>}
            {evaluateExtractError && <p className="upload-message error">{evaluateExtractError}</p>}
          </label>
          <label className="field">
            <span>Reference image (optional)</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={!supportsImages}
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const file = event.target.files?.[0] ?? null
                onImageChange(file)
              }}
            />
            {!supportsImages && (
              <small style={{ color: 'var(--muted)' }}>
                Image inputs are available when OpenAI is selected in settings.
              </small>
            )}
            {evaluateImage && (
              <small style={{ color: 'var(--ink)' }}>
                Selected: {evaluateImage.name}
              </small>
            )}
          </label>
        </div>
        <footer className="modal-footer">
          <button className="secondary ghost" type="button" onClick={onClose} disabled={evaluateStatus === 'loading'}>
            Cancel
          </button>
          <button className="primary" type="button" onClick={onRunEvaluation} disabled={evaluateStatus === 'loading'}>
            {evaluateStatus === 'loading' ? 'Running...' : 'Run assessment'}
          </button>
        </footer>
      </div>
    </div>
  )
}

export default EvaluateModal
