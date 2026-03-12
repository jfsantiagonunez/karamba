import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@/test/utils'
import MessageList from './MessageList'
import { mockMessages } from '@/test/mockData'

describe('MessageList', () => {
  describe('Unit Tests', () => {
    it('renders empty state when no messages', () => {
      render(<MessageList messages={[]} />)

      const container = screen.getByRole('list')
      expect(container).toBeInTheDocument()
      expect(container).toBeEmptyDOMElement()
    })

    it('renders user messages correctly', () => {
      const userMessages = mockMessages.filter(m => m.role === 'user')
      render(<MessageList messages={userMessages} />)

      expect(screen.getByText('What is artificial intelligence?')).toBeInTheDocument()
      expect(screen.getByText('What are its applications?')).toBeInTheDocument()
    })

    it('renders assistant messages with markdown', () => {
      const assistantMessages = mockMessages.filter(m => m.role === 'assistant')
      render(<MessageList messages={assistantMessages} />)

      expect(screen.getByText(/Artificial intelligence \(AI\) is/)).toBeInTheDocument()
      expect(screen.getByText(/AI has numerous applications/)).toBeInTheDocument()
    })

    it('displays citations when available', () => {
      const messageWithCitation = mockMessages.find(
        m => m.citations && m.citations.length > 0
      )!

      render(<MessageList messages={[messageWithCitation]} />)

      expect(screen.getByText(/Citations/)).toBeInTheDocument()
      expect(screen.getByText(/doc1\.pdf/)).toBeInTheDocument()
    })

    it('applies correct styling to user messages', () => {
      const userMessage = mockMessages[0]
      const { container } = render(<MessageList messages={[userMessage]} />)

      const messageElement = container.querySelector('.bg-blue-600')
      expect(messageElement).toBeInTheDocument()
      expect(messageElement).toHaveClass('text-white')
    })

    it('applies correct styling to assistant messages', () => {
      const assistantMessage = mockMessages[1]
      const { container } = render(<MessageList messages={[assistantMessage]} />)

      const messageElement = container.querySelector('.bg-gray-100')
      expect(messageElement).toBeInTheDocument()
    })

    it('renders all messages in order', () => {
      render(<MessageList messages={mockMessages} />)

      const messages = screen.getAllByRole('listitem')
      expect(messages).toHaveLength(mockMessages.length)
    })
  })

  describe('Accessibility', () => {
    it('has proper semantic HTML structure', () => {
      render(<MessageList messages={mockMessages} />)

      expect(screen.getByRole('list')).toBeInTheDocument()
      expect(screen.getAllByRole('listitem')).toHaveLength(mockMessages.length)
    })

    it('provides readable content for screen readers', () => {
      render(<MessageList messages={mockMessages} />)

      const userMessages = screen.getAllByText(/What is/)
      expect(userMessages.length).toBeGreaterThan(0)
    })
  })

  describe('Edge Cases', () => {
    it('handles messages with empty content gracefully', () => {
      const emptyMessage = { role: 'user' as const, content: '' }
      render(<MessageList messages={[emptyMessage]} />)

      const messages = screen.getAllByRole('listitem')
      expect(messages).toHaveLength(1)
    })

    it('handles very long messages', () => {
      const longMessage = {
        role: 'assistant' as const,
        content: 'A'.repeat(10000),
      }
      render(<MessageList messages={[longMessage]} />)

      expect(screen.getByText(/A{100,}/)).toBeInTheDocument()
    })

    it('handles special characters in messages', () => {
      const specialMessage = {
        role: 'user' as const,
        content: '<script>alert("xss")</script>',
      }
      render(<MessageList messages={[specialMessage]} />)

      // Should render as text, not execute
      expect(screen.getByText(/<script>alert/)).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('renders many messages without crashing', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        role: i % 2 === 0 ? ('user' as const) : ('assistant' as const),
        content: `Message ${i}`,
      }))

      render(<MessageList messages={manyMessages} />)

      const messages = screen.getAllByRole('listitem')
      expect(messages).toHaveLength(100)
    })
  })

  describe('Auto-scroll Behavior', () => {
    it('auto-scrolls to bottom when new messages are added', () => {
      const { rerender } = render(<MessageList messages={mockMessages.slice(0, 1)} />)

      // Mock scrollIntoView
      const scrollIntoViewMock = vi.fn()
      Element.prototype.scrollIntoView = scrollIntoViewMock

      // Add new message
      rerender(<MessageList messages={mockMessages} />)

      // Should have called scrollIntoView
      expect(scrollIntoViewMock).toHaveBeenCalled()
    })

    it('has a scroll anchor element at the bottom', () => {
      const { container } = render(<MessageList messages={mockMessages} />)

      // The last div should be the scroll anchor
      const scrollAnchor = container.querySelector('div:last-child')
      expect(scrollAnchor).toBeInTheDocument()
    })
  })
})
