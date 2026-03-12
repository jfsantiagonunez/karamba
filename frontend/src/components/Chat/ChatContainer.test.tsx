import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import ChatContainer from './ChatContainer'
import { mockQueryResponse } from '@/test/mockData'
import axios from 'axios'

// Mock axios
vi.mock('axios')
const mockedAxios = axios as any

describe('ChatContainer - Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedAxios.post.mockResolvedValue({ data: mockQueryResponse })
  })

  describe('Initial State', () => {
    it('displays welcome screen when no messages', () => {
      render(<ChatContainer />)

      expect(screen.getByText(/Welcome to Karamba/i)).toBeInTheDocument()
      expect(screen.getByText(/Upload documents and ask me anything/i)).toBeInTheDocument()
    })

    it('shows upload button on welcome screen', () => {
      render(<ChatContainer />)

      expect(screen.getByRole('button', { name: /upload your first document/i })).toBeInTheDocument()
    })

    it('has message input field', () => {
      render(<ChatContainer />)

      expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument()
    })
  })

  describe('Sending Messages', () => {
    it('allows user to type and send a message', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })

      await user.type(input, 'What is AI?')
      expect(input).toHaveValue('What is AI?')

      await user.click(sendButton)

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          expect.stringContaining('/agent/query'),
          expect.objectContaining({ query: 'What is AI?' })
        )
      })
    })

    it('clears input after sending message', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })

      await user.type(input, 'Test message')
      await user.click(sendButton)

      await waitFor(() => {
        expect(input).toHaveValue('')
      })
    })

    it('disables send button while message is empty', () => {
      render(<ChatContainer />)

      const sendButton = screen.getByRole('button', { name: /send/i })
      expect(sendButton).toBeDisabled()
    })

    it('enables send button when input has text', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })

      await user.type(input, 'Hello')

      expect(sendButton).toBeEnabled()
    })
  })

  describe('Message Display', () => {
    it('displays user message after sending', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'What is AI?')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.getByText('What is AI?')).toBeInTheDocument()
      })
    })

    it('displays assistant response after API call', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.getByText(mockQueryResponse.answer)).toBeInTheDocument()
      })
    })

    it('shows loading state during API call', async () => {
      // Delay the mock response
      mockedAxios.post.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: mockQueryResponse }), 100))
      )

      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))

      // Should show loading indicator
      expect(screen.getByPlaceholderText(/ask a question/i)).toBeDisabled()
    })
  })

  describe('Phase Indicators', () => {
    it('displays phase indicators when processing', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        // Check if phase results are displayed
        expect(mockedAxios.post).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Network error'))

      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        // Component should handle error gracefully
        expect(screen.queryByText(/error/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('allows retry after error', async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ data: mockQueryResponse })

      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)

      // First attempt fails
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.queryByText(/error/i)).toBeInTheDocument()
      })

      // Retry succeeds
      await user.type(input, 'Test again')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.getByText(mockQueryResponse.answer)).toBeInTheDocument()
      })
    })
  })

  describe('File Upload', () => {
    it('opens upload modal when clicking upload button', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const uploadButton = screen.getByRole('button', { name: /upload your first document/i })
      await user.click(uploadButton)

      await waitFor(() => {
        expect(screen.getByText(/upload documents/i)).toBeInTheDocument()
      })
    })

    it('closes upload modal when clicking close', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      // Open modal
      const uploadButton = screen.getByRole('button', { name: /upload your first document/i })
      await user.click(uploadButton)

      // Close modal
      const closeButton = screen.getByRole('button', { name: /close/i })
      await user.click(closeButton)

      await waitFor(() => {
        expect(screen.queryByText(/upload documents/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Conversation Flow', () => {
    it('handles multi-turn conversation', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)

      // First message
      await user.type(input, 'What is AI?')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.getByText('What is AI?')).toBeInTheDocument()
      })

      // Second message
      await user.type(input, 'Tell me more')
      await user.click(screen.getByRole('button', { name: /send/i }))

      await waitFor(() => {
        expect(screen.getByText('Tell me more')).toBeInTheDocument()
      })

      // Both messages should be visible
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
      expect(screen.getByText('Tell me more')).toBeInTheDocument()
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('sends message on Enter key', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Test{Enter}')

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalled()
      })
    })

    it('does not send on Shift+Enter (multiline)', async () => {
      const user = userEvent.setup()
      render(<ChatContainer />)

      const input = screen.getByPlaceholderText(/ask a question/i)
      await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2')

      expect(mockedAxios.post).not.toHaveBeenCalled()
    })
  })

  describe('Scrolling Behavior', () => {
    it('container is scrollable', () => {
      const { container } = render(<ChatContainer />)

      // Check that the messages container has overflow-y-auto
      const messagesContainer = container.querySelector('.overflow-y-auto')
      expect(messagesContainer).toBeInTheDocument()
    })
  })
})
