# Windows Setup Guide

## Quick Start (5 minutes)

### 1. Create Virtual Environment
```powershell
python -m venv venv
```

### 2. Activate Virtual Environment
```powershell
venv\Scripts\activate
```
*(You should see `(venv)` appear in your terminal)*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Install FFmpeg
**Option A: Using Chocolatey (Recommended)**
```powershell
choco install ffmpeg
```

**Option B: Manual Installation**
- Download from: https://www.gyan.dev/ffmpeg/builds/
- Extract to `C:\ffmpeg`
- Add `C:\ffmpeg\bin` to your PATH:
  1. Search "Environment Variables" in Windows
  2. Edit "Path" under System Variables
  3. Add new entry: `C:\ffmpeg\bin`
  4. Restart terminal
- Verify: `ffmpeg -version`

### 5. Setup API Key
Create `.env` file in project root:
```powershell
Set-Content -Path .env -Value "GEMINI_API_KEY=your_key_here"
```
Get free key from: https://makersuite.google.com/app/apikey

### 6. Run Web UI
```powershell
python app.py
```

Visit: http://127.0.0.1:5000

### 7. Run Command-Line Version
```powershell
python transcribe.py "https://instagram.com/reel/xyz"
```

## Deactivate Virtual Environment
```powershell
deactivate
```

## Troubleshooting

**"python not found"?**
- Install Python 3.10+ from https://python.org
- Check "Add to PATH" during installation

**"pip not found"?**
```powershell
python -m ensurepip --upgrade
```

**FFmpeg not working?**
- Verify PATH: `$env:PATH`
- Restart terminal after adding to PATH
- Use full path: `C:\ffmpeg\bin\ffmpeg.exe -version`

**Port 5000 already in use?**
Edit `app.py` line 67:
```python
app.run(debug=True, port=5001)
```

## Command Reference

**Check if in venv:**
```powershell
Get-Command python | Select-Object -ExpandProperty Path
```
Should show path inside `venv\Scripts\`

**Check environment variables:**
```powershell
Get-ChildItem Env:
```

**Force reinstall dependencies:**
```powershell
pip install --force-reinstall -r requirements.txt
```