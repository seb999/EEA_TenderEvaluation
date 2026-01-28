import type { AssessmentResult, Upload } from '../types'

type ReviewPanelProps = {
  selectedApplicant: Upload | null
  assessmentResults: AssessmentResult[]
  selectedQuestionId: string | null
  onSelectQuestion: (qId: string) => void
}

function ReviewPanel({
  selectedApplicant,
  assessmentResults,
  selectedQuestionId,
  onSelectQuestion,
}: ReviewPanelProps) {
  const selectedAssessment =
    assessmentResults.find((result) => result.q_id === selectedQuestionId) ?? null

  const scoreLabel =
    selectedAssessment?.score !== null && selectedAssessment?.score !== undefined
      ? `${selectedAssessment.score}`
      : 'N/A'

  const justification = selectedAssessment?.justification ?? ''
  const parsedResult = selectedAssessment?.parsed_result ?? null

  return (
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
              <span
                className={`pill ${
                  selectedApplicant?.status === 'completed' ? 'success' : 'muted'
                }`}
              >
                {selectedApplicant?.status ?? 'Not evaluated'}
              </span>
            </div>
            <button className="secondary" type="button">
              Re-run Evaluation
            </button>
            <button className="secondary" type="button">
              Export JSON
            </button>
            <div className="sidebar-list">
              {assessmentResults.length === 0 ? (
                <div className="question">No assessments yet</div>
              ) : (
                [...assessmentResults]
                  .sort((a, b) => {
                    const aNum = Number(a.q_id.match(/\d+/)?.[0] ?? Number.MAX_SAFE_INTEGER)
                    const bNum = Number(b.q_id.match(/\d+/)?.[0] ?? Number.MAX_SAFE_INTEGER)
                    if (aNum !== bNum) {
                      return aNum - bNum
                    }
                    return a.q_id.localeCompare(b.q_id)
                  })
                  .map((assessment) => {
                    const labelNumber = assessment.q_id.match(/\d+/)?.[0] ?? assessment.q_id

                    return (
                      <button
                        key={assessment.q_id}
                        className={`question ${assessment.q_id === selectedQuestionId ? 'active' : ''}`}
                        type="button"
                        onClick={() => onSelectQuestion(assessment.q_id)}
                      >
                        Question {labelNumber}
                      </button>
                    )
                  })
              )}
            </div>
          </div>
        </aside>

        <main className="review-main">
          <div className="card">
            {selectedApplicant ? (
              assessmentResults.length ? (
                <>
                  <h2>
                    {selectedQuestionId}: <span>{selectedAssessment?.question_text || 'Question'}</span>
                  </h2>
                  <div className="score-highlight">
                    <span className="score-label">Question score</span>
                    <span className="score-badge">{scoreLabel}</span>
                  </div>
                  <div className="callout">
                    <h3>Extracted Answer</h3>
                    <p>{selectedAssessment?.answer_text || 'No answer stored.'}</p>
                  </div>
                  <div className="assessment">
                    <div className="assessment-title">
                      <h3>Assessment & Score</h3>
                      <span className="score-badge">{scoreLabel}</span>
                    </div>
                    {justification ? <p>{justification}</p> : <p>No justification returned by the model.</p>}
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
  )
}

export default ReviewPanel
