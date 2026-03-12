import { useState } from 'react';
import ChatContainer from './ChatContainer';
import ChatSidebar from './ChatSidebar';

export default function ChatLayout() {
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    // Initialize with a new session ID
    return Date.now().toString();
  });

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const handleNewChat = () => {
    // Create a new session with timestamp as ID
    const newSessionId = Date.now().toString();
    setCurrentSessionId(newSessionId);
  };

  return (
    <div className="flex h-full bg-gray-100">
      <ChatSidebar
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />
      <div className="flex-1 flex flex-col bg-white">
        <ChatContainer sessionId={currentSessionId} />
      </div>
    </div>
  );
}
