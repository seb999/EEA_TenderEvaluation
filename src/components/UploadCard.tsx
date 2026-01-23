import { ChangeEvent, DragEvent, MouseEvent } from 'react'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

type UploadCardProps = {
  selectedFile: File | null
  vendorName: string
  uploadStatus: UploadStatus
  uploadMessage: string
  isDragging: boolean
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void
  onDragOver: (event: DragEvent<HTMLDivElement>) => void
  onDragLeave: (event: DragEvent<HTMLDivElement>) => void
  onDrop: (event: DragEvent<HTMLDivElement>) => void
  onUpload: (event: MouseEvent<HTMLButtonElement>) => void
  onVendorChange: (value: string) => void
  onBrowse: () => void
}

function UploadCard({
  selectedFile,
  vendorName,
  uploadStatus,
  uploadMessage,
  isDragging,
  onFileChange,
  onDragOver,
  onDragLeave,
  onDrop,
  onUpload,
  onVendorChange,
  onBrowse,
}: UploadCardProps) {
  return (
    <div className="card upload-card">
      <h2>Upload New Application</h2>
      <div
        className={`dropzone ${isDragging ? 'dragging' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <div>
          <p>{selectedFile ? selectedFile.name : 'Drag & drop your PDF file here'}</p>
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={onFileChange}
            style={{ display: 'none' }}
          />
          <button className="link-button" type="button" onClick={onBrowse}>
            Browse
          </button>
        </div>
      </div>
      <label className="field">
        <span>Applicant Name</span>
        <input
          placeholder="Vendor name"
          value={vendorName}
          onChange={(event) => onVendorChange(event.target.value)}
        />
      </label>
      {uploadMessage && <p className={`upload-message ${uploadStatus}`}>{uploadMessage}</p>}
      <button className="primary" onClick={onUpload} disabled={uploadStatus === 'uploading'}>
        {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload & Process'}
      </button>
    </div>
  )
}

export default UploadCard
