from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Secure Healthcare API is running!"}
