# Frontend Testing Guide

## Overview

This guide covers the testing strategy for the Karamba frontend application. We use **Vitest** (fast, Vite-compatible) with **React Testing Library** for comprehensive test coverage.

---

## Test Strategy

### Testing Pyramid

```
        E2E (5%)
         /\
        /  \
       /    \
   Integration (70%)     ← Focus here!
      /      \
     /        \
   Unit (25%)
```

**Why Integration-Focused?**
- Chat interfaces are interaction-heavy
- Integration tests catch real user flows
- Less brittle than isolated unit tests
- Better ROI for effort invested

---

## Setup

### Install Dependencies

```bash
cd frontend
npm install
```

**Test Dependencies Added:**
- `vitest` - Fast test runner (Vite-native)
- `@testing-library/react` - React component testing
- `@testing-library/user-event` - User interaction simulation
- `@testing-library/jest-dom` - DOM matchers
- `@vitest/ui` - Visual test UI
- `@vitest/coverage-v8` - Coverage reporting
- `jsdom` - DOM environment for Node
- `msw` - API mocking (Mock Service Worker)

### Configuration Files

**[vitest.config.ts](vitest.config.ts)**
- Vitest configuration
- Coverage settings
- Path aliases

**[src/test/setup.ts](src/test/setup.ts)**
- Global test setup
- DOM cleanup
- Browser API mocks

**[src/test/utils.tsx](src/test/utils.tsx)**
- Custom render function with providers
- QueryClient setup for tests

**[src/test/mockData.ts](src/test/mockData.ts)**
- Mock messages, documents, API responses

---

## Running Tests

### Commands

```bash
# Run all tests
npm test

# Run tests in watch mode (default)
npm test

# Run tests once (CI mode)
npm test -- --run

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- MessageList.test.tsx

# Run tests matching pattern
npm test -- --grep "user message"
```

### Watch Mode

Vitest runs in **watch mode** by default:
- Tests re-run on file changes
- Fast feedback loop
- Press `a` to run all tests
- Press `f` to run failed tests only

---

## Writing Tests

### Test Types

#### 1. Unit Tests

**Purpose:** Test individual components in isolation

**Example:** [MessageList.test.tsx](src/components/Chat/MessageList.test.tsx)

```typescript
import { render, screen } from '@/test/utils'
import MessageList from './MessageList'

it('renders user messages correctly', () => {
  const messages = [{ role: 'user', content: 'Hello' }]
  render(<MessageList messages={messages} />)

  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

**When to use:**
- Pure presentational components
- Utility functions
- Custom hooks
- Complex logic isolated from UI

#### 2. Integration Tests

**Purpose:** Test component interactions and user flows

**Example:** [ChatContainer.test.tsx](src/components/Chat/ChatContainer.test.tsx)

```typescript
import { render, screen, waitFor } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import ChatContainer from './ChatContainer'

it('allows user to send a message', async () => {
  const user = userEvent.setup()
  render(<ChatContainer />)

  const input = screen.getByPlaceholderText(/ask a question/i)
  await user.type(input, 'What is AI?')
  await user.click(screen.getByRole('button', { name: /send/i }))

  await waitFor(() => {
    expect(screen.getByText('What is AI?')).toBeInTheDocument()
  })
})
```

**When to use:**
- User workflows (type → send → receive)
- API integration
- State changes
- Multiple component interaction

---

## Test Organization

### Naming Conventions

```
ComponentName.test.tsx    - Component tests
utils.test.ts             - Utility function tests
integration.test.tsx      - Cross-component integration
```

### Test Structure

```typescript
describe('ComponentName', () => {
  describe('Feature/Behavior', () => {
    it('does something specific', () => {
      // Arrange
      const props = { ... }

      // Act
      render(<Component {...props} />)

      // Assert
      expect(screen.getByText('...')).toBeInTheDocument()
    })
  })
})
```

### Test Categories

```typescript
describe('MessageList', () => {
  describe('Unit Tests', () => { ... })
  describe('Accessibility', () => { ... })
  describe('Edge Cases', () => { ... })
  describe('Performance', () => { ... })
})
```

---

## Common Patterns

### 1. Rendering with Providers

```typescript
import { render } from '@/test/utils'  // Custom render with QueryClient

render(<Component />)  // Automatically wrapped
```

### 2. User Interactions

```typescript
import userEvent from '@testing-library/user-event'

const user = userEvent.setup()
await user.type(input, 'text')
await user.click(button)
await user.selectOptions(select, 'option')
```

### 3. Async Testing

```typescript
import { waitFor } from '@/test/utils'

await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument()
})

// Or use findBy queries (built-in waitFor)
expect(await screen.findByText('Loaded')).toBeInTheDocument()
```

### 4. API Mocking

```typescript
import { vi } from 'vitest'
import axios from 'axios'

vi.mock('axios')
const mockedAxios = axios as any

mockedAxios.post.mockResolvedValue({ data: mockResponse })
```

### 5. Component Queries

```typescript
// Prefer accessible queries
screen.getByRole('button', { name: /submit/i })
screen.getByLabelText('Email')
screen.getByPlaceholderText('Enter text')

// Fallbacks
screen.getByTestId('custom-element')
screen.getByText(/exact or regex/)
```

---

## Coverage Goals

### Target Coverage

- **Statements:** 80%+
- **Branches:** 75%+
- **Functions:** 80%+
- **Lines:** 80%+

### View Coverage

```bash
npm run test:coverage
```

**Output:**
- Terminal summary
- HTML report: `coverage/index.html`

### Coverage Configuration

Excludes (see `vitest.config.ts`):
- `node_modules/`
- `src/test/` (test utilities)
- `*.d.ts` (type definitions)
- `*.config.*` (config files)
- `dist/` (build output)

---

## Best Practices

### ✅ DO

- **Test user behavior, not implementation**
  ```typescript
  // Good
  await user.click(screen.getByRole('button', { name: /send/i }))
  expect(screen.getByText('Sent!')).toBeInTheDocument()

  // Bad
  expect(component.state.isSent).toBe(true)
  ```

- **Use accessible queries**
  ```typescript
  screen.getByRole('button')      // Best
  screen.getByLabelText('Name')   // Good
  screen.getByTestId('submit')    // Last resort
  ```

- **Test from user perspective**
  ```typescript
  // User sees "Loading...", then "Success!"
  expect(screen.getByText('Loading...')).toBeInTheDocument()
  await waitFor(() => {
    expect(screen.getByText('Success!')).toBeInTheDocument()
  })
  ```

- **Use mock data**
  ```typescript
  import { mockMessages } from '@/test/mockData'
  render(<MessageList messages={mockMessages} />)
  ```

### ❌ DON'T

- **Don't test implementation details**
  ```typescript
  // Bad
  expect(wrapper.find('.class-name')).toExist()
  expect(component.props.onClick).toHaveBeenCalled()
  ```

- **Don't use brittle selectors**
  ```typescript
  // Bad
  container.querySelector('.css-class-123')
  ```

- **Don't test third-party libraries**
  ```typescript
  // Don't test React Query, axios, etc.
  // Test YOUR code that uses them
  ```

---

## Debugging Tests

### Visual Debugging

```bash
npm run test:ui
```

Opens interactive UI at `http://localhost:51204`

### Debug in VS Code

Add to `.vscode/launch.json`:

```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Vitest",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["run", "test"],
  "console": "integratedTerminal"
}
```

### Print Debug Info

```typescript
import { screen } from '@/test/utils'

// Print DOM tree
screen.debug()

// Print specific element
screen.debug(screen.getByRole('button'))

// Print all available roles
screen.logTestingPlaygroundURL()
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test -- --run
      - run: npm run test:coverage
```

---

## Examples

### Unit Test Example

**File:** `src/components/Chat/MessageList.test.tsx`

```typescript
describe('MessageList', () => {
  it('renders user messages with correct styling', () => {
    const { container } = render(
      <MessageList messages={[{ role: 'user', content: 'Test' }]} />
    )

    expect(container.querySelector('.bg-blue-600')).toBeInTheDocument()
  })
})
```

### Integration Test Example

**File:** `src/components/Chat/ChatContainer.test.tsx`

```typescript
describe('ChatContainer', () => {
  it('handles complete send-receive flow', async () => {
    const user = userEvent.setup()
    mockedAxios.post.mockResolvedValue({ data: mockResponse })

    render(<ChatContainer />)

    // Type message
    await user.type(screen.getByPlaceholderText(/ask/i), 'Hello')

    // Send message
    await user.click(screen.getByRole('button', { name: /send/i }))

    // Verify API called
    expect(mockedAxios.post).toHaveBeenCalledWith(
      expect.stringContaining('/query'),
      expect.objectContaining({ query: 'Hello' })
    )

    // Verify response displayed
    await waitFor(() => {
      expect(screen.getByText(mockResponse.answer)).toBeInTheDocument()
    })
  })
})
```

---

## Troubleshooting

### "Cannot find module '@/test/utils'"

**Solution:** Check `tsconfig.json` has path alias:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### "window.matchMedia is not a function"

**Solution:** Already handled in `src/test/setup.ts`

### "IntersectionObserver is not defined"

**Solution:** Already handled in `src/test/setup.ts`

### Tests timing out

**Solution:** Increase timeout:

```typescript
await waitFor(() => { ... }, { timeout: 5000 })
```

---

## Resources

- [Vitest Docs](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [User Event API](https://testing-library.com/docs/user-event/intro)
- [Common Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

## Next Steps

1. ✅ **Set up testing infrastructure** - Done!
2. ✅ **Write example tests** - Done!
3. ⏭️ **Add more component tests** - MessageInput, PhaseIndicator
4. ⏭️ **Add E2E tests** - Playwright/Cypress for full flows
5. ⏭️ **Integrate with CI/CD** - Run tests on every PR

---

**Happy Testing! 🧪**
