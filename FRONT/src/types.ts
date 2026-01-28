export type Upload = {
  id: number
  filename: string
  vendor_name: string
  file_size: number
  uploaded_at: number
  status: string
  evaluation_score?: number | null
  evaluation_result?: {
    evaluations?: Record<
      string,
      {
        question_text?: string
        answer_text?: string
        parsed_result?: unknown
        llm_response?: string
      }
    >
    last_updated?: string
  } | null
}

export type Question = {
  id: number
  q_id: string
  prompt_json: {
    question?: string
    scale?: string
    required_evidence?: string[]
    evaluation_guidance?: string[]
    output_format?: Record<string, string>
    weight?: number
  }
}

export type AssessmentResult = {
  id: number
  applicant_id: number
  q_id: string
  question_text: string
  answer_text: string
  score: number | null
  justification: string | null
  llm_response: string
  parsed_result: unknown
  created_at: string
}
