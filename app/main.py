from fastapi import FastAPI

app = FastAPI(title="FELLAH.AI")

@app.get("/")
def read_root():
    return {
        "status": "FELLAH.AI is online",
        "role": "Personne B - Infrastructure",
        "message": "En attente du travail de Zineb"
    }