#!/bin/bash

echo "🚀 Starting Karamba - Full Stack"
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux to run both servers..."
    
    # Create new tmux session
    tmux new-session -d -s karamba
    
    # Window 1: Backend
    tmux rename-window -t karamba:0 'backend'
    tmux send-keys -t karamba:0 'cd backend && source venv/bin/activate && cd src && uvicorn api.main:app --reload' C-m
    
    # Window 2: Frontend
    tmux new-window -t karamba:1 -n 'frontend'
    tmux send-keys -t karamba:1 'cd frontend && npm run dev' C-m
    
    # Attach to session
    tmux attach-session -t karamba
else
    echo "tmux not found. Starting in current terminal..."
    echo "Open a second terminal and run: ./start-frontend.sh"
    echo ""
    ./start-backend.sh
fi
