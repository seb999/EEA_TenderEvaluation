import { ChangeEvent } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faInfoCircle } from '@fortawesome/free-solid-svg-icons'
import type { Question } from '../types'

type EvaluateModalProps = {
  vendorName: string
  questions: Question[]
  evaluateQuestion: string
  evaluateAnswer: string
  evaluateStatus: 'idle' | 'loading'
  evaluateExtracting: boolean
  evaluateExtractError: string
  showWorkflowInfo: boolean
  onToggleWorkflowInfo: () => void
  onClose: () => void
  onQuestionChange: (value: string) => void
  onAnswerChange: (value: string) => void
  onAnswerBlur: () => void
  onRunEvaluation: () => void
}

function EvaluateModal({
  vendorName,
  questions,
  evaluateQuestion,
  evaluateAnswer,
  evaluateStatus,
  evaluateExtracting,
  evaluateExtractError,
  showWorkflowInfo,
  onToggleWorkflowInfo,
  onClose,
  onQuestionChange,
  onAnswerChange,
  onAnswerBlur,
  onRunEvaluation,
}: EvaluateModalProps) {
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
                  <strong>Select a question:</strong> The system first checks if an answer has already been stored.
                </li>
                <li>
                  <strong>Auto-extraction:</strong> If none is stored, it extracts the relevant section from the PDF and saves it.
                </li>
                <li>
                  <strong>Manual override:</strong> You can edit or paste an answer. It saves when you leave the field.
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
          <label className="field">
            <span>Proposal answer</span>
            <textarea
              className="modal-textarea"
              value={evaluateAnswer}
              onChange={(event: ChangeEvent<HTMLTextAreaElement>) => onAnswerChange(event.target.value)}
              onBlur={onAnswerBlur}
              placeholder="Paste the answer from the proposal"
              rows={10}
            />
            {evaluateExtracting && <p className="upload-message uploading">Extracting proposal answer...</p>}
            {evaluateExtractError && <p className="upload-message error">{evaluateExtractError}</p>}
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
