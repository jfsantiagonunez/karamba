import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { File, Upload } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import {
  getConversationHistory,
  uploadDocument,
  streamQueryConversation,
  streamApproveAction,
  StreamEvent,
} from '../../services/api';
import PhaseIndicator from '../Agent/PhaseIndicator';
import MessageInput from './MessageInput';
import MessageList from './MessageList';
import LinkedDocuments from './LinkedDocuments';
import ApprovalModal from './ApprovalModal';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  phaseResults?: any[];
  citations?: any[];
  agentId?: string;
  agentName?: string;
  routingConfidence?: number;
  routingReasoning?: string;
}

interface ChatContainerProps {
  sessionId: string;
}

export default function ChatContainer({ sessionId }: ChatContainerProps) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentPhases, setCurrentPhases] = useState<any[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgentName, setCurrentAgentName] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<{
    actionId: string;
    query: string;
    reason: string;
    agentName?: string;
  } | null>(null);
  const streamingRef = useRef<boolean>(false);

  // Load conversation history when session changes
  const { data: historyData, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['conversation-history', sessionId],
    queryFn: () => getConversationHistory(sessionId),
    enabled: !!sessionId,
    retry: false, // Don't retry if session doesn't exist yet
  });

  // Update messages when history loads
  useEffect(() => {
    if (historyData?.messages) {
      const loadedMessages: Message[] = historyData.messages.map((msg, idx) => ({
        id: `${sessionId}-${idx}`,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        citations: msg.metadata?.citations,
        agentId: msg.metadata?.agent_id,
        agentName: msg.metadata?.agent_name,
        routingConfidence: msg.metadata?.routing_confidence,
        routingReasoning: msg.metadata?.routing_reasoning,
      }));
      setMessages(loadedMessages);
    } else {
      // New session, clear messages
      setMessages([]);
    }
  }, [sessionId, historyData]);

  // Helper function to map agent_id to friendly name
  const getAgentName = (agentId?: string) => {
    if (!agentId) return undefined;
    if (agentId === 'research_agent') return 'Research Assistant';
    if (agentId === 'financial_risk_agent') return 'Financial Risk Analyst';
    return agentId;
  };

  // Handle streaming events
  const handleStreamEvent = (event: StreamEvent) => {
    console.log('Stream event:', event);

    switch (event.type) {
      case 'routing':
        if (event.status === 'completed') {
          setCurrentAgentName(event.agent_name || null);
        }
        break;

      case 'approval_required':
        setPendingApproval({
          actionId: event.pending_action.action_id,
          query: event.pending_action.query,
          reason: event.pending_action.reason,
          agentName: event.agent_name,
        });
        setCurrentPhases([]);
        setIsProcessing(false);
        break;

      case 'phase':
        // Update phase status in real-time
        setCurrentPhases((prev) => {
          const existingPhase = prev.find((p) => p.name === event.phase_name);

          if (existingPhase) {
            // Update existing phase
            return prev.map((p) =>
              p.name === event.phase_name
                ? { ...p, status: event.status }
                : p
            );
          } else {
            // Add new phase
            return [...prev, { name: event.phase_name, status: event.status }];
          }
        });
        break;

      case 'complete':
        const assistantMessage: Message = {
          id: Date.now().toString() + '-assistant',
          role: 'assistant',
          content: event.answer || '(No response content)',
          timestamp: new Date(),
          phaseResults: event.phase_results,
          citations: event.citations,
          agentId: event.agent_id,
          agentName: event.agent_name || currentAgentName || undefined,
          routingConfidence: event.routing_confidence,
          routingReasoning: event.routing_reasoning,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setCurrentPhases([]);
        setIsProcessing(false);
        setPendingApproval(null);
        streamingRef.current = false;
        break;

      case 'error':
        const errorMessage: Message = {
          id: Date.now().toString() + '-error',
          role: 'assistant',
          content: `Error: ${event.error || 'Failed to process query'}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        setCurrentPhases([]);
        setIsProcessing(false);
        streamingRef.current = false;
        break;
    }
  };

  const handleStreamError = (error: Error) => {
    console.error('Stream error:', error);
    const errorMessage: Message = {
      id: Date.now().toString() + '-error',
      role: 'assistant',
      content: `Connection error: ${error.message}`,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, errorMessage]);
    setCurrentPhases([]);
    setIsProcessing(false);
    streamingRef.current = false;
  };

  const handleStreamComplete = () => {
    console.log('Stream complete');
    streamingRef.current = false;
  };

  const handleApprove = () => {
    if (pendingApproval && !streamingRef.current) {
      setIsProcessing(true);
      streamingRef.current = true;
      setCurrentPhases([]);

      streamApproveAction(
        sessionId,
        pendingApproval.actionId,
        handleStreamEvent,
        handleStreamError,
        handleStreamComplete
      );

      // Close the modal immediately
      setPendingApproval(null);
    }
  };

  const handleDeny = () => {
    const denialMessage: Message = {
      id: Date.now().toString() + '-denial',
      role: 'assistant',
      content: '❌ Query execution denied by user.',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, denialMessage]);
    setPendingApproval(null);
  };

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, sessionId),
    onSuccess: (response) => {
      setSelectedFile(null);
      setShowUpload(false);

      // Invalidate session documents query to refresh the linked documents display
      queryClient.invalidateQueries({ queryKey: ['session-documents', sessionId] });

      const successMessage: Message = {
        id: Date.now().toString() + '-upload',
        role: 'assistant',
        content: `✅ Document "${response.filename}" uploaded successfully and linked to this chat! You can now ask questions about it.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, successMessage]);
    },
    onError: (error: any) => {
      const errorMessage: Message = {
        id: Date.now().toString() + '-upload-error',
        role: 'assistant',
        content: `❌ Upload failed: ${error.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    },
  });

  const handleSendMessage = (content: string) => {
    if (streamingRef.current || isProcessing) {
      console.log('Already processing a query');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString() + '-user',
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setCurrentPhases([]);
    setIsProcessing(true);
    streamingRef.current = true;

    streamQueryConversation(
      sessionId,
      content,
      false,
      handleStreamEvent,
      handleStreamError,
      handleStreamComplete
    );
  };

  const handleFileUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  if (isLoadingHistory) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading conversation...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Linked Documents Indicator */}
      <LinkedDocuments sessionId={sessionId} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4 max-w-md px-4">
              <div className="text-6xl">🤖</div>
              <h2 className="text-2xl font-semibold text-gray-900">
                Welcome to Karamba
              </h2>
              <p className="text-gray-600">
                Upload documents and ask me anything. I'll automatically route your question to the right specialist agent.
              </p>
              <div className="flex flex-col gap-2 items-center">
                <button
                  onClick={() => setShowUpload(true)}
                  className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  <Upload size={20} />
                  <span>Upload Document</span>
                </button>
                <p className="text-sm text-gray-500">
                  Or just start chatting below
                </p>
              </div>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Upload Document</h3>

            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                {selectedFile ? (
                  <div className="flex items-center justify-center space-x-2">
                    <File size={20} className="text-blue-600" />
                    <span className="text-sm">{selectedFile.name}</span>
                  </div>
                ) : (
                  <>
                    <Upload className="mx-auto text-gray-400 mb-2" size={32} />
                    <input
                      type="file"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                      accept=".pdf,.docx,.csv,.xlsx,.txt,.md"
                      className="hidden"
                      id="quick-upload"
                    />
                    <label
                      htmlFor="quick-upload"
                      className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Choose a file
                    </label>
                    <p className="text-xs text-gray-500 mt-2">
                      PDF, DOCX, CSV, XLSX, TXT, MD
                    </p>
                  </>
                )}
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => {
                    setShowUpload(false);
                    setSelectedFile(null);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFileUpload}
                  disabled={!selectedFile || uploadMutation.isPending}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Phase Indicator */}
      {isProcessing && currentPhases.length > 0 && (
        <div className="border-t border-gray-200 bg-white p-4">
          <PhaseIndicator phases={currentPhases} />
        </div>
      )}

      {/* Input with Upload Button */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex items-center space-x-2 mb-2">
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Upload size={16} />
            <span>Upload</span>
          </button>
        </div>
        <MessageInput onSend={handleSendMessage} disabled={isProcessing} />
      </div>

      {/* Approval Modal */}
      {pendingApproval && (
        <ApprovalModal
          actionId={pendingApproval.actionId}
          query={pendingApproval.query}
          reason={pendingApproval.reason}
          agentName={pendingApproval.agentName}
          onApprove={handleApprove}
          onDeny={handleDeny}
          isProcessing={isProcessing}
        />
      )}
    </div>
  );
}
