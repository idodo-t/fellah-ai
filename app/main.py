import os
import httpx
from fastapi import FastAPI, Form, Response, Depends
from sqlalchemy.orm import Session
from twilio.rest import Client
from dotenv import load_dotenv
from app.database import SessionLocal, init_db
from app.services.agents import process_message, LocationWeatherAgent

# 1. Chargement des variables d'environnement
load_dotenv()
init_db()
app = FastAPI()

# Configuration Twilio (SID et Token)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(None), 
    From: str = Form(None), 
    MediaUrl0: str = Form(None), 
    MediaContentType0: str = Form(None), 
    Latitude: str = Form(None), 
    Longitude: str = Form(None), 
    db: Session = Depends(get_db)
):
    print(f"\n--- 📥 SIGNAL REÇU DE {From} ---")
    
    image_bytes, audio_bytes, text_content = None, None, (Body or "").strip()
    
    # 2. Téléchargement de l'image avec Authentification Twilio
    if MediaUrl0:
        print(f"DEBUG: Téléchargement de l'image sécurisée...")
        try:
            # On utilise le SID et Token pour avoir le droit de lire l'image
            async with httpx.AsyncClient(auth=(TWILIO_SID, TWILIO_TOKEN), timeout=15.0) as client:
                resp = await client.get(MediaUrl0, follow_redirects=True)
                if resp.status_code == 200:
                    image_bytes = resp.content
                    print("✅ Image téléchargée et prête pour l'analyse !")
                else:
                    print(f"⚠️ Erreur téléchargement : Code {resp.status_code}")
        except Exception as e:
            print(f"❌ Erreur réseau lors du téléchargement : {e}")

    # 3. Traitement par l'IA (On envoie les 7 arguments attendus)
    if Latitude and Longitude:
        print("DEBUG: Signal Localisation reçu.")
        lat, lon = float(Latitude), float(Longitude)
        w = LocationWeatherAgent.fetch_weather(lat, lon)
        msg = LocationWeatherAgent.format(lat, lon, "Région démo", w, "culture", "french")
    else:
        print("DEBUG: Appel du cerveau IA (process_message)...")
        # On passe : phone, text, img_bytes, img_mime, audio_bytes, audio_mime, db
        msg = process_message(From, text_content, image_bytes, MediaContentType0, audio_bytes, MediaContentType0, db)

    print(f"DEBUG: Réponse générée : {msg[:50]}...")

    # 4. ENVOI DIRECT SUR WHATSAPP (Méthode PUSH)
    try:
        twilio_client.messages.create(
            from_="whatsapp:+14155238886", # Numéro officiel du Sandbox
            body=msg,
            to=From
        )
        print("🚀 SUCCÈS : Le diagnostic a été envoyé sur WhatsApp !")
    except Exception as e:
        print(f"❌ ERREUR D'ENVOI TWILIO : {e}")

    # 5. Réponse XML vide pour satisfaire Twilio
    return Response(content="<Response></Response>", media_type="application/xml")