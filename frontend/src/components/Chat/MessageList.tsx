import { useEffect, useRef } from 'react';
import { Message } from './ChatContainer';
import ReactMarkdown from 'react-markdown';

interface Props {
  messages: Message[];
}

// Agent badge component
function AgentBadge({ agentId, agentName }: { agentId?: string; agentName?: string }) {
  if (!agentId) return null;

  const displayName = agentName || agentId;
  const badgeColor = agentId === 'research_agent'
    ? 'bg-blue-100 text-blue-800'
    : agentId === 'financial_risk_agent'
    ? 'bg-green-100 text-green-800'
    : 'bg-gray-100 text-gray-800';

  const icon = agentId === 'financial_risk_agent' ? '📊' : '📚';

  return (
    <div className="mb-2">
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badgeColor}`}>
        <span>{icon}</span>
        <span>{displayName}</span>
      </span>
    </div>
  );
}

export default function MessageList({ messages }: Props) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-auto p-6 space-y-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-3xl rounded-lg p-4 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-900'
            }`}
          >
            {/* Show agent badge for assistant messages */}
            {message.role === 'assistant' && message.agentId && (
              <AgentBadge agentId={message.agentId} agentName={message.agentName} />
            )}

            <ReactMarkdown className="text-gray-900">{message.content}</ReactMarkdown>

            {message.citations && message.citations.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-sm font-semibold mb-2">Sources:</p>
                {message.citations.map((citation, idx) => (
                  <div key={idx} className="text-sm text-gray-600 mb-1">
                    • {citation.document_id} (score: {citation.score.toFixed(2)})
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
      {/* Invisible element at the bottom for auto-scroll */}
      <div ref={messagesEndRef} />
    </div>
  );
}