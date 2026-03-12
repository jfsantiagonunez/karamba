# One-time setup
./setup.sh

# Start with Docker
docker-compose up -d

# OR start manually
# Terminal 1 (Backend)
cd backend && source venv/bin/activate && cd src && uvicorn api.main:app --reload

# Terminal 2 (Frontend)
cd frontend && npm run dev

# Access at http://localhost:5173