"""Convenience launcher:  python run.py  ->  http://127.0.0.1:8000"""
import os

import uvicorn #type:ignore

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8001")),
        reload=bool(os.environ.get("RELOAD")),
    )
