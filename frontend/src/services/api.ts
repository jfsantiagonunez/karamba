import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface QueryRequest {
  query: string;
  document_ids?: string[];
  session_id?: string;
}

export interface PhaseResult {
  phase_name: string;
  phase_type: string;
  status: string;
  output: string;
  metadata: Record<string, any>;
}

export interface QueryResponse {
  answer: string;
  phase_results: PhaseResult[];
  citations: Array<{
    content: string;
    document_id: string;
    score: number;
  }>;
  session_id: string;
  agent_id?: string;
  agent_name?: string;
  routing_confidence?: number;
  routing_reasoning?: string;
  requires_approval?: boolean;
  pending_action?: any;
}

export interface Document {
  filename: string;
  size: number;
  modified: number;
  linked_sessions?: Array<{
    session_id: string;
    title: string;
  }>;
}

export interface DocumentStats {
  total_chunks: number;
  collection_name: string;
}

// Agent API
export const queryAgent = async (request: QueryRequest): Promise<QueryResponse> => {
  const response = await api.post('/api/v1/agent/query', request);
  return response.data;
};

export const getAgentStats = async (): Promise<DocumentStats> => {
  const response = await api.get('/api/v1/agent/stats');
  return response.data;
};

// Document API
export const uploadDocument = async (
  file: File,
  sessionId?: string
): Promise<{ document_id: string; filename: string; session_id?: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const response = await api.post('/api/v1/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const deleteDocument = async (documentId: string): Promise<void> => {
  await api.delete(`/api/v1/documents/${documentId}`);
};

export const listDocuments = async (sessionId?: string): Promise<{
  documents: Document[];
  stats: DocumentStats;
  session_id?: string;
  document_count?: number;
}> => {
  const params = sessionId ? { session_id: sessionId } : {};
  const response = await api.get('/api/v1/documents/list', { params });
  return response.data;
};

export const getSessionDocuments = async (sessionId: string): Promise<{
  session_id: string;
  documents: Document[];
  document_count: number;
}> => {
  const response = await api.get(`/api/v1/documents/session/${sessionId}`);
  return response.data;
};

// WebSocket for streaming
export const createWebSocket = (sessionId: string) => {
  const wsUrl = API_URL.replace('http', 'ws');
  return new WebSocket(`${wsUrl}/ws/agent/${sessionId}`);
};

// Conversation/Session API
export interface SessionInfo {
  session_id: string;
  title: string;
  last_activity: string;
  message_count: number;
  document_count: number;
}

export const listSessions = async (): Promise<{ sessions: SessionInfo[]; total_count: number }> => {
  const response = await api.get('/api/v1/conversations/');
  return response.data;
};

export const getConversationHistory = async (sessionId: string): Promise<{
  session_id: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
    metadata: Record<string, any>;
  }>;
  message_count: number;
}> => {
  const response = await api.get(`/api/v1/conversations/${sessionId}/history`);
  return response.data;
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/api/v1/conversations/${sessionId}`);
};

export const queryConversation = async (
  sessionId: string,
  request: { query: string; document_ids?: string[]; approved?: boolean }
): Promise<QueryResponse> => {
  const response = await api.post(`/api/v1/conversations/${sessionId}/query`, request);
  return response.data;
};

export const approveAction = async (
  sessionId: string,
  actionId: string
): Promise<QueryResponse> => {
  const response = await api.post(`/api/v1/conversations/${sessionId}/approve`, {
    action_id: actionId,
  });
  return response.data;
};

// Streaming API
export interface StreamEvent {
  type: 'routing' | 'approval_required' | 'phase' | 'complete' | 'error';
  status?: string;
  message?: string;
  agent_id?: string;
  agent_name?: string;
  confidence?: number;
  reasoning?: string;
  pending_action?: any;
  phase_name?: string;
  phase_type?: string;
  output?: string;
  answer?: string;
  citations?: Array<{
    content: string;
    document_id: string;
    score: number;
  }>;
  phase_results?: PhaseResult[];
  routing_confidence?: number;
  routing_reasoning?: string;
  error?: string;
}

export const streamQueryConversation = async (
  sessionId: string,
  query: string,
  approved: boolean = false,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> => {
  const url = `${API_URL}/api/v1/conversations/${sessionId}/query/stream?query=${encodeURIComponent(query)}&approved=${approved}`;

  console.log('!!! FRONTEND: Starting stream to:', url);

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No reader available');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onComplete?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            console.log('SSE event received:', data.type, data.phase_name);
            onEvent(data);

            // Close connection if complete or error
            if (data.type === 'complete' || data.type === 'error') {
              reader.cancel();
              onComplete?.();
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', line, e);
          }
        }
      }
    }
  } catch (error) {
    onError?.(error as Error);
  }
};

export const streamApproveAction = async (
  sessionId: string,
  actionId: string,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> => {
  const url = `${API_URL}/api/v1/conversations/${sessionId}/approve/stream?action_id=${encodeURIComponent(actionId)}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No reader available');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onComplete?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            console.log('SSE event received:', data.type, data.phase_name);
            onEvent(data);

            // Close connection if complete or error
            if (data.type === 'complete' || data.type === 'error') {
              reader.cancel();
              onComplete?.();
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', line, e);
          }
        }
      }
    }
  } catch (error) {
    onError?.(error as Error);
  }
};

export default api;