# 🪟 Running SmartShop AI on Windows

## Prerequisites

1. **Python 3.11+** installed
2. **Git** (optional, for version control)
3. **PowerShell** or **Command Prompt**

---

## 🚀 Quick Start (Windows)

### Step 1: Open PowerShell in Project Directory

```powershell
# Navigate to your project folder
cd "C:\Users\to_dh\AppData\Roaming\Claude\local-agent-mode-sessions\...\local_smartAIShope\smartshop-ai"
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate
```

You should see `(venv)` in your prompt.

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment

Edit the `.env` file and update:
```
OPENAI_API_KEY=your-actual-openai-key-here
```

### Step 5: Run the Application

**Terminal 1 - FastAPI Backend:**
```powershell
python app/main.py
```

You should see:
```
🚀 Starting SmartShop AI v1.0.0
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Streamlit UI:** (Open a new PowerShell window)
```powershell
cd "C:\Users\to_dh\AppData\Roaming\Claude\...\smartshop-ai"
.\venv\Scripts\activate
streamlit run app/ui/streamlit_app.py
```

### Step 6: Access the Application

Open your browser:
- **Streamlit UI**: http://localhost:8501
- **FastAPI API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🐳 Option 2: Run with Docker on Windows

### Prerequisites
- Docker Desktop for Windows installed and running

### Steps

1. **Open PowerShell in project directory**

2. **Build and run with Docker Compose:**
```powershell
docker-compose up --build
```

3. **Access the application:**
   - Streamlit UI: http://localhost:8501
   - FastAPI: http://localhost:8000

---

## 🛑 Troubleshooting

### Port Already in Use (Error: Address already in use)

If port 8000 or 8501 is already taken:

**Find what's using the port:**
```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :8501
```

**Kill the process:**
```powershell
taskkill /PID <process-id> /F
```

Or change the port in the code:
- FastAPI: Edit `app/core/config.py` → `API_PORT = 8080`
- Streamlit: Run with `streamlit run app/ui/streamlit_app.py --server.port 8502`

### Virtual Environment Not Activating

Make sure PowerShell execution policy allows scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Module Not Found Errors

Ensure you're in the virtual environment:
```powershell
.\venv\Scripts\activate
pip list  # Verify packages are installed
```

If missing, reinstall:
```powershell
pip install -r requirements.txt
```

---

## 📝 Notes

- **The Linux VM app I started is NOT accessible from Windows** - it's in an isolated sandbox
- **You need to run the app directly on your Windows machine** using the steps above
- **Your shared folder** already has all the files needed

---

## ✅ Verification

Once running, test:
```powershell
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", "service": "SmartShop AI"}
```

---

**Need help?** Let me know if you encounter any errors!
