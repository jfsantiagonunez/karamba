import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Plus, Trash2, Loader2, FileText } from 'lucide-react';
import { listSessions, deleteSession, type SessionInfo } from '../../services/api';

interface ChatSidebarProps {
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
}

export default function ChatSidebar({
  currentSessionId,
  onSelectSession,
  onNewChat,
}: ChatSidebarProps) {
  const queryClient = useQueryClient();

  // Fetch list of sessions
  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: listSessions,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      // If deleted current session, create new chat
      const deletedCurrentSession = sessionsData?.sessions.some(
        (s: SessionInfo) => s.session_id === currentSessionId
      );
      if (currentSessionId && deletedCurrentSession) {
        onNewChat();
      }
    },
  });

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this chat? This action cannot be undone.')) {
      deleteMutation.mutate(sessionId);
    }
  };

  const formatLastActivity = (lastActivity: string) => {
    const date = new Date(lastActivity);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          <span className="font-medium">New Chat</span>
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="animate-spin text-gray-400" size={24} />
          </div>
        ) : sessionsData?.sessions && sessionsData.sessions.length > 0 ? (
          <div className="p-2 space-y-1">
            {sessionsData.sessions.map((session: SessionInfo) => (
              <div
                key={session.session_id}
                onClick={() => onSelectSession(session.session_id)}
                className={`
                  group relative flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                  ${
                    session.session_id === currentSessionId
                      ? 'bg-blue-100 text-blue-900'
                      : 'hover:bg-gray-100 text-gray-700'
                  }
                `}
              >
                <MessageSquare
                  size={18}
                  className={session.session_id === currentSessionId ? 'text-blue-600' : 'text-gray-400'}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {session.title}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                    <span>{formatLastActivity(session.last_activity)}</span>
                    {session.document_count > 0 && (
                      <>
                        <span>•</span>
                        <FileText size={12} className="inline" />
                        <span>{session.document_count}</span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(session.session_id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 size={14} className="text-red-600" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-gray-500">
            <MessageSquare size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No chats yet</p>
            <p className="text-xs mt-1">Click "New Chat" to start</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 text-center">
          {sessionsData?.total_count || 0} chat{sessionsData?.total_count !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}
