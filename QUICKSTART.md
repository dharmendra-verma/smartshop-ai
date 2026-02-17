# 🚀 SmartShop AI - Quick Start Guide

## ⚡ Get Started in 5 Minutes

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Run the Application

**Option A: Run Backend & Frontend Separately**

Terminal 1 - Start FastAPI backend:
```bash
python app/main.py
```

Terminal 2 - Start Streamlit UI:
```bash
streamlit run app/ui/streamlit_app.py
```

**Option B: Use Docker** (if Docker is installed)

```bash
docker-compose up --build
```

### 4. Access the Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📝 Next Steps

### Phase 1: Foundation (Current)
- ✅ Project structure created
- ⏳ Set up PostgreSQL database → See `SCRUM-6`
- ⏳ Create data ingestion pipeline → See `SCRUM-7`
- ⏳ Load product catalog → See `SCRUM-8`

### Phase 2: Build Agents
- Implement Product Recommendation Agent
- Implement Review Summarization Agent
- Connect agents to UI

---

## 🐛 Troubleshooting

**Backend won't start:**
- Make sure port 8000 is not in use
- Check that `.env` file exists with valid OpenAI API key
- Verify all dependencies are installed: `pip list`

**UI won't connect to backend:**
- Ensure FastAPI is running on port 8000
- Check the API URL in Streamlit sidebar settings
- Try visiting http://localhost:8000/health directly

**Module import errors:**
- Make sure you activated the virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`

---

## 📚 Documentation

- **Full Documentation**: See `README.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Jira Board**: https://projecttracking.atlassian.net/jira/software/projects/SCRUM/boards

---

**Need help?** Check the README.md or ask on the team channel!

🤖 *Built with Claude Sonnet 4.5*
