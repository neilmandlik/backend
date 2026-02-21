#!/bin/bash
export PYTHONPATH=/app:$PYTHONPATH
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT
