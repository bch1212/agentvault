"""Allow running as: python -m api"""
from api.main import app
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
