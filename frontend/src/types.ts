export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  phaseResults?: PhaseResult[]
  citations?: Citation[]
  agentId?: string
  agentName?: string
  routingConfidence?: number
  routingReasoning?: string
}

export interface PhaseResult {
  phase_name: string
  phase_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  output: string
  verification_results: VerificationResult[]
  metadata?: Record<string, any>
  error?: string
}

export interface VerificationResult {
  passed: boolean
  rule_name: string
  message: string
  score?: number
}

export interface Citation {
  content: string
  document_id: string
  score: number
}

export interface Document {
  id: string
  name: string
  size: number
  uploaded_at: string
}

export interface QueryResponse {
  answer: string
  phase_results: PhaseResult[]
  citations: Citation[]
  session_id: string
  agent_id?: string
  agent_name?: string
  routing_confidence?: number
  routing_reasoning?: string
  requires_approval?: boolean
  pending_action?: any
}

export interface ConversationQueryRequest {
  query: string
  document_ids?: string[]
  approved?: boolean
}

export interface ConversationHistory {
  session_id: string
  messages: ConversationMessage[]
  message_count: number
}

export interface ConversationMessage {
  role: string
  content: string
  timestamp: string
  metadata: Record<string, any>
}

export interface AgentInfo {
  agent_id: string
  name: string
  description: string
  capabilities: string[]
  keywords: string[]
  example_queries: string[]
}

export interface AvailableAgentsResponse {
  agents: AgentInfo[]
  total_count: number
}
