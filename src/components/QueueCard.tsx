import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTrash, faWandMagicSparkles } from '@fortawesome/free-solid-svg-icons'
import type { Upload } from '../types'

type QueueCardProps = {
  uploads: Upload[]
  selectedApplicantId: number | null
  onSelectApplicant: (id: number) => void
  onEvaluate: (vendorName: string, applicantId: number) => void
  onDelete: (applicantId: number, vendorName: string) => void
}

function QueueCard({
  uploads,
  selectedApplicantId,
  onSelectApplicant,
  onEvaluate,
  onDelete,
}: QueueCardProps) {
  const formatUploadLabel = (upload: Upload) => {
    const vendor = upload.vendor_name?.trim()
    const filename = upload.filename?.trim()

    if (!vendor) {
      return filename || 'Unnamed file'
    }

    if (filename && filename.toLowerCase().includes(vendor.toLowerCase())) {
      return filename
    }

    return filename ? `${vendor} - ${filename}` : vendor
  }

  return (
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
              <span>{formatUploadLabel(upload)}</span>
              <span className="pill success">Uploaded</span>
              <div className="queue-actions">
                <button
                  className={`secondary ghost ${selectedApplicantId === upload.id ? 'active' : ''}`}
                  type="button"
                  onClick={() => onSelectApplicant(upload.id)}
                >
                  View Details
                </button>
                <button
                  className="icon-button evaluate-button"
                  type="button"
                  onClick={() => onEvaluate(upload.vendor_name, upload.id)}
                  title="Run LLM assessment"
                >
                  <FontAwesomeIcon icon={faWandMagicSparkles} />
                </button>
                <button
                  className="icon-button delete-button"
                  type="button"
                  onClick={() => onDelete(upload.id, upload.vendor_name)}
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
  )
}

export default QueueCard
