from fastapi import FastAPI

app = FastAPI(title="Media Tracker")

@app.get("/health")
def health_check():
    return {"status": "ok"}
