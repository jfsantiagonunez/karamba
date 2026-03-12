"""Example: Using conversation memory and human-in-the-loop features."""
import asyncio
from karamba.memory import SessionStore, ConversationOrchestrator
from karamba.core.agent import KarambaAgent
from karamba.llm import LLMConfig


async def basic_conversation_example():
    """Example 1: Basic multi-turn conversation."""
    print("=" * 60)
    print("Example 1: Basic Multi-Turn Conversation")
    print("=" * 60)

    # Initialize components
    llm_config = LLMConfig(
        provider="ollama",
        model="llama3.2:3b",
        temperature=0.7
    )

    agent = KarambaAgent(
        llm_config=llm_config,
        vector_store_path="./data/vector_store"
    )

    async with SessionStore(db_path="./data/sessions.db") as store:
        orchestrator = ConversationOrchestrator(
            agent=agent,
            session_store=store,
            enable_reflection=False
        )

        session_id = "example-session-1"

        # First query
        print("\n👤 User: What is artificial intelligence?")
        result1 = await orchestrator.query(
            session_id=session_id,
            query="What is artificial intelligence?"
        )
        print(f"🤖 Assistant: {result1['answer'][:200]}...")

        # Follow-up query (agent remembers context!)
        print("\n👤 User: What are its main applications?")
        result2 = await orchestrator.query(
            session_id=session_id,
            query="What are its main applications?"
        )
        print(f"🤖 Assistant: {result2['answer'][:200]}...")

        # Another follow-up
        print("\n👤 User: Are there any risks?")
        result3 = await orchestrator.query(
            session_id=session_id,
            query="Are there any risks?"
        )
        print(f"🤖 Assistant: {result3['answer'][:200]}...")

        # View conversation history
        print("\n" + "=" * 60)
        print("Conversation History")
        print("=" * 60)

        history = await orchestrator.get_conversation(session_id)
        for i, msg in enumerate(history, 1):
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            print(f"\n{i}. {role_emoji} {msg['role'].upper()}: {msg['content'][:100]}...")


async def human_in_the_loop_example():
    """Example 2: Human-in-the-loop approval workflow."""
    print("\n\n" + "=" * 60)
    print("Example 2: Human-in-the-Loop Workflow")
    print("=" * 60)

    llm_config = LLMConfig(
        provider="ollama",
        model="llama3.2:3b",
        temperature=0.7
    )

    agent = KarambaAgent(
        llm_config=llm_config,
        vector_store_path="./data/vector_store"
    )

    async with SessionStore(db_path="./data/sessions.db") as store:
        orchestrator = ConversationOrchestrator(
            agent=agent,
            session_store=store,
            enable_reflection=False
        )

        session_id = "example-session-2"

        # Query that triggers approval
        print("\n👤 User: Delete all documents about testing")
        result = await orchestrator.query(
            session_id=session_id,
            query="Delete all documents about testing"
        )

        if result["requires_approval"]:
            print("\n⚠️  APPROVAL REQUIRED!")
            print(f"Action Type: {result['pending_action']['action_type']}")
            print(f"Reason: {result['pending_action']['reason']}")
            print(f"Query: {result['pending_action']['query']}")

            # Simulate human approval
            print("\n🤔 Human reviews the request...")
            print("✅ Human approves the action")

            # Continue execution
            result = await orchestrator.approve_and_continue(
                session_id=session_id,
                action_id=result["pending_action"]["action_id"]
            )

            print(f"\n🤖 Assistant: {result['answer']}")
        else:
            print(f"\n🤖 Assistant: {result['answer']}")


async def session_management_example():
    """Example 3: Session management operations."""
    print("\n\n" + "=" * 60)
    print("Example 3: Session Management")
    print("=" * 60)

    async with SessionStore(db_path="./data/sessions.db") as store:
        # Create multiple sessions
        session1 = await store.create_session("demo-session-1")
        session2 = await store.create_session("demo-session-2")
        session3 = await store.create_session("demo-session-3")

        print(f"\n✅ Created 3 sessions")

        # Add messages to sessions
        await store.add_message("demo-session-1", "user", "Hello")
        await store.add_message("demo-session-1", "assistant", "Hi there!")
        await store.add_message("demo-session-2", "user", "How are you?")

        # List all sessions
        sessions = await store.list_sessions()
        count = await store.get_session_count()

        print(f"\n📋 Active sessions: {count}")
        for session_id in sessions:
            state = await store.get_session(session_id)
            msg_count = state.conversation_history.get_message_count()
            print(f"  - {session_id}: {msg_count} messages")

        # Get conversation history
        print("\n💬 History for demo-session-1:")
        history = await store.get_conversation_history("demo-session-1")
        for msg in history.messages:
            print(f"  {msg.role.value}: {msg.content}")

        # Clear conversation
        print("\n🗑️  Clearing conversation for demo-session-1...")
        await store.clear_conversation("demo-session-1")

        history = await store.get_conversation_history("demo-session-1")
        print(f"  Messages after clear: {len(history.messages)}")

        # Delete session
        print("\n❌ Deleting demo-session-3...")
        await store.delete_session("demo-session-3")

        remaining = await store.get_session_count()
        print(f"  Remaining sessions: {remaining}")


async def reflection_example():
    """Example 4: Self-reflection pattern (future feature)."""
    print("\n\n" + "=" * 60)
    print("Example 4: Self-Reflection Pattern (Coming Soon)")
    print("=" * 60)

    llm_config = LLMConfig(
        provider="ollama",
        model="llama3.2:3b",
        temperature=0.7
    )

    agent = KarambaAgent(
        llm_config=llm_config,
        vector_store_path="./data/vector_store"
    )

    async with SessionStore(db_path="./data/sessions.db") as store:
        # Enable reflection
        orchestrator = ConversationOrchestrator(
            agent=agent,
            session_store=store,
            enable_reflection=True,
            max_reflection_iterations=2
        )

        session_id = "example-session-4"

        print("\n👤 User: Explain quantum computing")
        print("\n🔄 Agent will:")
        print("  1. Generate initial answer")
        print("  2. Reflect on quality")
        print("  3. Improve if quality < 80%")
        print("  4. Repeat until satisfied or max iterations")

        result = await orchestrator.query(
            session_id=session_id,
            query="Explain quantum computing"
        )

        print(f"\n🤖 Final Answer (after {result.get('reflection_count', 0)} reflections):")
        print(f"   Quality Score: {result.get('quality_score', 'N/A')}")
        print(f"   {result['answer'][:200]}...")


async def main():
    """Run all examples."""
    print("🚀 Karamba Conversation Memory Examples")
    print("=" * 60)

    try:
        # Example 1: Basic conversation
        await basic_conversation_example()

        # Example 2: Human-in-the-loop
        await human_in_the_loop_example()

        # Example 3: Session management
        await session_management_example()

        # Example 4: Reflection (if enabled)
        # await reflection_example()

        print("\n\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
