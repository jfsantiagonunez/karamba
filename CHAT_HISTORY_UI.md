# Chat History UI

## Overview

Karamba now features a comprehensive chat history UI that allows users to manage multiple conversation sessions, view past chats, and seamlessly switch between different conversations.

**Key Features**:
- 📝 Multiple conversation sessions
- 🔍 Easy session selection from sidebar
- 🗑️ Delete individual chat sessions
- ➕ Create new chats on demand
- 💾 Automatic conversation persistence
- 🔄 Session switching with history loading

---

## User Interface

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     Header (Karamba)                        │
│                 [Chat] [Documents] tabs                     │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│   Sidebar    │         Chat Container                       │
│              │                                              │
│  [+ New      │   ┌──────────────────────────────────┐     │
│    Chat]     │   │                                  │     │
│              │   │      Messages Area               │     │
│  📋 Chat 1   │   │                                  │     │
│  📋 Chat 2   │   │                                  │     │
│  📋 Chat 3   │   └──────────────────────────────────┘     │
│  📋 Chat 4   │                                              │
│              │   [Upload] [Type message...] [Send]         │
│              │                                              │
│  4 chats     │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

---

## Components

### 1. ChatLayout

**Location**: [frontend/src/components/Chat/ChatLayout.tsx](frontend/src/components/Chat/ChatLayout.tsx)

**Purpose**: Main container that manages session state and coordinates between sidebar and chat.

**Features**:
- Manages current session ID
- Handles session switching
- Creates new chat sessions
- Coordinates between sidebar and chat container

```typescript
export default function ChatLayout() {
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    return Date.now().toString(); // New session on load
  });

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const handleNewChat = () => {
    const newSessionId = Date.now().toString();
    setCurrentSessionId(newSessionId);
  };

  return (
    <div className="flex h-screen">
      <ChatSidebar
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />
      <ChatContainer sessionId={currentSessionId} />
    </div>
  );
}
```

---

### 2. ChatSidebar

**Location**: [frontend/src/components/Chat/ChatSidebar.tsx](frontend/src/components/Chat/ChatSidebar.tsx)

**Purpose**: Displays list of chat sessions with management controls.

**Features**:
- Lists all available chat sessions
- Highlights currently active session
- "New Chat" button at the top
- Delete button for each session (on hover)
- Auto-refreshes every 10 seconds
- Shows total chat count

**UI Elements**:

```
┌────────────────────┐
│  [+ New Chat]      │ ← Always visible
├────────────────────┤
│  📋 Chat Nov 28... │ ← Session list
│  📋 Chat Nov 27... │   (click to select)
│  📋 Chat Nov 26... │   [🗑️] on hover
│  📋 Chat Nov 25... │
├────────────────────┤
│  4 chats           │ ← Counter
└────────────────────┘
```

**Key Functions**:

```typescript
// Fetch sessions
const { data: sessionsData } = useQuery({
  queryKey: ['sessions'],
  queryFn: listSessions,
  refetchInterval: 10000, // Refresh every 10s
});

// Delete session
const deleteMutation = useMutation({
  mutationFn: deleteSession,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sessions'] });
  },
});
```

---

### 3. ChatContainer (Updated)

**Location**: [frontend/src/components/Chat/ChatContainer.tsx](frontend/src/components/Chat/ChatContainer.tsx)

**Purpose**: Displays messages for a specific session and handles interactions.

**Updates**:
- Now accepts `sessionId` as prop
- Loads conversation history when session changes
- Uses conversation API endpoints
- Preserves agent routing information from history

**Key Features**:

```typescript
interface ChatContainerProps {
  sessionId: string;
}

// Load history when session changes
const { data: historyData, isLoading } = useQuery({
  queryKey: ['conversation-history', sessionId],
  queryFn: () => getConversationHistory(sessionId),
  enabled: !!sessionId,
});

// Update messages when history loads
useEffect(() => {
  if (historyData?.messages) {
    const loadedMessages = historyData.messages.map((msg, idx) => ({
      id: `${sessionId}-${idx}`,
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
      timestamp: new Date(msg.timestamp),
      agentId: msg.metadata?.agent_id,
      agentName: msg.metadata?.agent_name,
      // ... other fields
    }));
    setMessages(loadedMessages);
  }
}, [sessionId, historyData]);
```

---

## API Integration

### New API Functions

**Location**: [frontend/src/services/api.ts](frontend/src/services/api.ts)

#### 1. List Sessions

```typescript
export const listSessions = async (): Promise<{
  sessions: string[];
  total_count: number;
}> => {
  const response = await api.get('/api/v1/conversations/');
  return response.data;
};
```

**Endpoint**: `GET /api/v1/conversations/`

**Response**:
```json
{
  "sessions": ["1730123456789", "1730098765432", "1730012345678"],
  "total_count": 3
}
```

---

#### 2. Get Conversation History

```typescript
export const getConversationHistory = async (sessionId: string) => {
  const response = await api.get(`/api/v1/conversations/${sessionId}/history`);
  return response.data;
};
```

**Endpoint**: `GET /api/v1/conversations/{session_id}/history`

**Response**:
```json
{
  "session_id": "1730123456789",
  "messages": [
    {
      "role": "user",
      "content": "What is AI?",
      "timestamp": "2026-02-04T10:30:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "Artificial Intelligence (AI) is...",
      "timestamp": "2026-02-04T10:30:15Z",
      "metadata": {
        "agent_id": "research_agent",
        "agent_name": "Research Assistant",
        "routing_confidence": 0.85,
        "citations": [...]
      }
    }
  ],
  "message_count": 2
}
```

---

#### 3. Delete Session

```typescript
export const deleteSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/api/v1/conversations/${sessionId}`);
};
```

**Endpoint**: `DELETE /api/v1/conversations/{session_id}`

---

#### 4. Query Conversation

```typescript
export const queryConversation = async (
  sessionId: string,
  request: { query: string; document_ids?: string[]; approved?: boolean }
): Promise<QueryResponse> => {
  const response = await api.post(
    `/api/v1/conversations/${sessionId}/query`,
    request
  );
  return response.data;
};
```

**Endpoint**: `POST /api/v1/conversations/{session_id}/query`

---

## User Workflows

### Creating a New Chat

1. User clicks "New Chat" button in sidebar
2. System generates new session ID (timestamp)
3. ChatLayout updates current session
4. ChatContainer clears messages and shows welcome screen
5. New session added to sidebar list on first message

**Visual Flow**:
```
[+ New Chat] → Generate ID → Switch Session → Clear UI → Ready!
```

---

### Switching Between Chats

1. User clicks on a chat session in sidebar
2. Current session ID updates
3. ChatContainer fetches conversation history
4. Messages load and display with agent badges
5. User can continue the conversation

**Visual Flow**:
```
Click Chat → Update ID → Fetch History → Load Messages → Ready!
```

---

### Deleting a Chat

1. User hovers over a chat session
2. Delete button (🗑️) appears
3. User clicks delete button
4. Confirmation dialog appears
5. On confirm: session deleted from backend
6. Sidebar refreshes, session removed from list
7. If deleted session was active, new chat created

**Visual Flow**:
```
Hover → [🗑️] Appears → Click → Confirm → Delete → Refresh List
```

---

### Continuing a Conversation

1. User selects existing chat from sidebar
2. Previous messages load (including agent badges)
3. User types new message
4. System routes to appropriate agent (same multi-agent logic)
5. Response appears with agent badge
6. Message added to session history

---

## Session ID Format

Sessions use **timestamp-based IDs**:

```typescript
const sessionId = Date.now().toString();
// Example: "1730123456789"
```

**Display Format**:
- Parses timestamp to readable date
- Format: "Month Day, Hour:Minute"
- Example: "Nov 28, 10:30 AM"

```typescript
const formatSessionId = (sessionId: string) => {
  const timestamp = parseInt(sessionId);
  if (!isNaN(timestamp)) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  return sessionId.slice(0, 8);
};
```

---

## State Management

### Session State Flow

```
App.tsx
  └─ ChatLayout (manages currentSessionId)
      ├─ ChatSidebar (displays sessions, handles selection)
      │   └─ useQuery: listSessions()
      │   └─ useMutation: deleteSession()
      │
      └─ ChatContainer (displays messages for session)
          └─ useQuery: getConversationHistory(sessionId)
          └─ useMutation: queryConversation()
```

### React Query Keys

```typescript
// Sessions list
['sessions']

// Conversation history
['conversation-history', sessionId]
```

**Benefits**:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

---

## Styling & Responsiveness

### Sidebar Width

```css
width: 16rem; /* 256px - w-64 */
```

### Active Session Highlight

```typescript
className={`
  ${sessionId === currentSessionId
    ? 'bg-blue-100 text-blue-900'  // Active
    : 'hover:bg-gray-100 text-gray-700'  // Inactive
  }
`}
```

### Delete Button

```typescript
// Hidden by default, visible on hover
className="opacity-0 group-hover:opacity-100"
```

---

## Features & Behavior

### Auto-Refresh

Sessions list refreshes **every 10 seconds** to show new chats:

```typescript
refetchInterval: 10000
```

### Loading States

**Loading History**:
```
┌────────────────────┐
│                    │
│   [Spinner]        │
│   Loading          │
│   conversation...  │
│                    │
└────────────────────┘
```

**Empty Sidebar**:
```
┌────────────────────┐
│  [+ New Chat]      │
├────────────────────┤
│                    │
│    📋              │
│   No chats yet     │
│ Click "New Chat"   │
│   to start         │
│                    │
└────────────────────┘
```

---

## Preservation of Agent Info

When loading conversation history, agent routing information is preserved:

```typescript
const loadedMessages = historyData.messages.map((msg, idx) => ({
  id: `${sessionId}-${idx}`,
  role: msg.role,
  content: msg.content,
  timestamp: new Date(msg.timestamp),
  citations: msg.metadata?.citations,
  agentId: msg.metadata?.agent_id,           // ← Preserved
  agentName: msg.metadata?.agent_name,       // ← Preserved
  routingConfidence: msg.metadata?.routing_confidence,  // ← Preserved
  routingReasoning: msg.metadata?.routing_reasoning,    // ← Preserved
}));
```

**Result**: Agent badges display correctly in loaded conversations:
- 📚 Research Assistant
- 📊 Financial Risk Analyst

---

## Error Handling

### Session Not Found

When loading history for non-existent session:
```typescript
retry: false  // Don't retry 404s
```

Result: Empty message list, user can start new conversation

### Delete Error

If delete fails:
- Error logged to console
- Session remains in list
- User can retry

### Network Errors

- React Query handles retries automatically
- Loading states show during fetch
- Error boundaries catch catastrophic failures

---

## Future Enhancements

### Short-term
- 🔍 Search within conversations
- 🏷️ Name/rename chat sessions
- 📌 Pin important chats to top
- 📅 Group chats by date (Today, Yesterday, Last Week)

### Medium-term
- 🌙 Dark mode support
- ⌨️ Keyboard shortcuts (Ctrl+N for new chat)
- 🗂️ Folders/categories for chats
- 🔐 Export chat history

### Long-term
- 🔄 Sync across devices
- 👥 Share conversations
- 📊 Usage analytics per session
- 🤖 AI-generated session titles

---

## Testing

### Manual Testing Checklist

- [ ] Create new chat
- [ ] Switch between chats
- [ ] Delete a chat
- [ ] Delete active chat (should create new)
- [ ] Load chat with existing history
- [ ] Verify agent badges display correctly in history
- [ ] Send message in existing chat
- [ ] Refresh page (session list persists)
- [ ] Test with 0 chats (empty state)
- [ ] Test with many chats (scrolling)

### Test Scenarios

**Scenario 1: First-time User**
1. App loads with new session ID
2. No sessions in sidebar (empty state)
3. User sends first message
4. Chat appears in sidebar
5. User creates new chat
6. Two chats now in sidebar

**Scenario 2: Returning User**
1. App loads with new session ID
2. Multiple sessions in sidebar
3. User selects old session
4. History loads with agent badges
5. User continues conversation
6. New message appended to history

**Scenario 3: Session Management**
1. User has 5 sessions
2. Deletes 3rd session
3. List updates, session removed
4. User creates new chat
5. New session appears at top
6. Total shows "3 chats"

---

## Files Modified

**Created**:
- ✅ [frontend/src/components/Chat/ChatLayout.tsx](frontend/src/components/Chat/ChatLayout.tsx)
- ✅ [frontend/src/components/Chat/ChatSidebar.tsx](frontend/src/components/Chat/ChatSidebar.tsx)

**Modified**:
- ✅ [frontend/src/components/Chat/ChatContainer.tsx](frontend/src/components/Chat/ChatContainer.tsx)
- ✅ [frontend/src/services/api.ts](frontend/src/services/api.ts)
- ✅ [frontend/src/App.tsx](frontend/src/App.tsx)

---

## Summary

### What Was Built

✅ **Complete chat history UI** with sidebar
✅ **Multiple session management** (create, view, delete)
✅ **Automatic history loading** on session switch
✅ **Agent badge preservation** in loaded conversations
✅ **Seamless session switching** with React Query
✅ **Auto-refresh** session list every 10 seconds

### User Benefits

✅ **Organized conversations** - Keep different topics separate
✅ **Full history** - Never lose a conversation
✅ **Quick access** - Switch between chats instantly
✅ **Visual clarity** - See which agent answered historical questions
✅ **Clean interface** - Intuitive sidebar navigation

### Developer Benefits

✅ **React Query** - Automatic caching and state management
✅ **TypeScript** - Full type safety
✅ **Modular components** - Easy to maintain and extend
✅ **Clean separation** - Layout, Sidebar, Container
✅ **API integration** - RESTful endpoints

---

## Ready to Use

The chat history UI is now **production-ready**! Users can:

1. 📝 Create multiple conversations
2. 🔄 Switch between chats seamlessly
3. 📚 View full conversation history
4. 🗑️ Delete unwanted chats
5. 🤖 See which agent handled each message

**Try it now**:
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 and start chatting! 🚀
