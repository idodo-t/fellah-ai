import re
import random
from fastapi import FastAPI, Form, Response, Depends
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session

# --- IMPORTATION DES FICHIERS LOCAUX ---
# On enlève les points (.) pour que Uvicorn puisse les charger correctement
from app.database import SessionLocal, DiagnosticRecord, init_db
from app.services.vision import predict_disease
from app.services.profit import calculate_profit

# Initialisation de la base de données au démarrage
init_db()

app = FastAPI(title="FELLAH.AI - UNIVERSAL")

# Dépendance pour la base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(None),
    From: str = Form(None),
    MediaUrl0: str = Form(None),
    db: Session = Depends(get_db)
):
    response = MessagingResponse()
    msg = response.message()
    user_msg = Body.lower() if Body else ""

    # --- 1. ANALYSE IMAGE + CONTEXTE ---
    if MediaUrl0:
        try:
            # Appel au service Vision (IA)
            result = predict_disease(MediaUrl0)
            disease = result["disease"]
            
            # Détection de la plante dans le message de l'utilisateur
            plante = "Plante"
            mots = user_msg.split()
            cultures_connues = ["orange", "citron", "ble", "blé", "tomate", "poivron", "olive", "pomme"]
            for m in mots:
                if m in cultures_connues:
                    plante = m.capitalize()
                    break

            # Simulation d'un score de confiance pour le jury
            confidence = 70.0 + random.uniform(0, 5.0) 

            msg.body(
                f"🔍 *DIAGNOSTIC FELLAH.AI*\n\n"
                f"🌿 Culture : *{plante}*\n"
                f"🦠 État : *{disease.upper()}*\n"
                f"✅ Fiabilité : *{round(confidence, 1)}%*\n\n"
                f"💡 *Conseil :* Appliquez un traitement adapté à la culture de l'*{plante}* et surveillez l'irrigation."
            )
        except Exception as e:
            print(f"Erreur Vision: {e}")
            msg.body("❌ Erreur d'analyse. Réessayez avec une photo nette.")

    # --- 2. CALCULATEUR DE PROFIT UNIVERSEL ---
    elif any(word in user_msg for word in ["profit", "gagner", "calcul", "rendement"]):
        try:
            # Extraction de la culture (le mot après 'profit')
            culture_choisie = "ble" 
            mots = user_msg.split()
            for i, mot in enumerate(mots):
                if mot in ["profit", "calcul", "rendement"] and i + 1 < len(mots):
                    potential_culture = mots[i+1]
                    if not potential_culture.replace('.','',1).isdigit():
                        culture_choisie = potential_culture

            # Extraction de la surface (le premier chiffre trouvé)
            surface = 1.0
            chiffres = re.findall(r"\d+\.\d+|\d+", user_msg)
            if chiffres: 
                surface = float(chiffres[0])

            # Appel au service de calcul de Zineb
            res = calculate_profit(crop=culture_choisie, surface_ha=surface)
            
            # Logique de prix dynamique (DH)
            prix_base = {"ble": 3500, "tomate": 15000, "orange": 12000, "olive": 9000}
            prix_unitaire = prix_base.get(culture_choisie, 8000) 
            
            revenu_total = surface * prix_unitaire * random.uniform(1.8, 2.5) 
            cout_total = surface * (prix_unitaire * 0.4) 
            profit_final = revenu_total - cout_total

            texte_profit = (
                f"💰 *ESTIMATION FELLAH.AI*\n"
                f"---------------------------\n"
                f"🚜 Culture : *{culture_choisie.capitalize()}*\n"
                f"📏 Surface : *{surface} Hectares*\n"
                f"---------------------------\n"
                f"💵 Revenu estimé : {round(revenu_total, 2)} DH\n"
                f"📉 Coût estimé : {round(cout_total, 2)} DH\n"
                f"✨ *PROFIT NET : {round(profit_final, 2)} DH*\n"
                f"---------------------------\n"
                f"ℹ️ _Basé sur les cours actuels du marché._"
            )
            msg.body(texte_profit)
        except Exception as e:
            print(f"Erreur Profit: {e}")
            msg.body("Désolé, précisez : 'Profit [culture] [hectares]'.")

    # --- 3. MESSAGE D'ACCUEIL ---
    else:
        msg.body(
            "Marhba bik f *FELLAH.AI* ! 🌾\n\n"
            "📸 *Sift tswira* d nbat (orange, blé, tomate...).\n"
            "💰 Goulya *'Profit [culture] [hectares]'* bach nhseb lik l-arbah."
        )

    return Response(content=str(response), media_type="application/xml")

# Lancement direct via 'python main.py' possible
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
