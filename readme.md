# 1. Create project folder

mkdir bank-parser-backend
cd bank-parser-backend

# 2. Create virtual environment

py -3.13 -m venv .venv

# 3. Activate virtual environment

# On Windows PowerShell

.\.venv\Scripts\Activate.ps1

# On macOS/Linux

source .venv/bin/activate

# 4. Install dependencies

pip install --upgrade pip
pip install -r requirements.txt

# 5. Run the Server

uvicorn main:app --reload --port 8000
