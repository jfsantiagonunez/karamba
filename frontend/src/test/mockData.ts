import { Message, PhaseResult } from '../types'

export const mockMessages: Message[] = [
  {
    role: 'user',
    content: 'What is artificial intelligence?',
  },
  {
    role: 'assistant',
    content: 'Artificial intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems.',
    phaseResults: [],
    citations: [],
  },
  {
    role: 'user',
    content: 'What are its applications?',
  },
  {
    role: 'assistant',
    content: 'AI has numerous applications including natural language processing, computer vision, robotics, and expert systems.',
    phaseResults: [],
    citations: [
      {
        content: 'AI is used in healthcare for diagnosis...',
        document_id: 'doc1.pdf',
        score: 0.95,
      },
    ],
  },
]

export const mockPhaseResults: PhaseResult[] = [
  {
    phase_name: 'planning',
    phase_type: 'planning',
    status: 'completed',
    output: 'Breaking down the query into sub-questions...',
    verification_results: [],
  },
  {
    phase_name: 'retrieval',
    phase_type: 'retrieval',
    status: 'completed',
    output: 'Retrieved 5 relevant chunks from documents',
    verification_results: [],
  },
  {
    phase_name: 'reasoning',
    phase_type: 'reasoning',
    status: 'completed',
    output: 'Analyzing retrieved information...',
    verification_results: [],
  },
]

export const mockDocuments = [
  {
    id: 'doc1',
    name: 'AI Research Paper.pdf',
    size: 1024000,
    uploaded_at: '2026-02-03T10:00:00Z',
  },
  {
    id: 'doc2',
    name: 'Machine Learning Guide.pdf',
    size: 2048000,
    uploaded_at: '2026-02-03T11:00:00Z',
  },
]

export const mockQueryResponse = {
  answer: 'This is a test answer from the agent.',
  phase_results: mockPhaseResults,
  citations: [
    {
      content: 'Relevant excerpt from document...',
      document_id: 'doc1',
      score: 0.92,
    },
  ],
  session_id: 'test-session-123',
}
