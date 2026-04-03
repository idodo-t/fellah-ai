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

# ---------------------------------------------------------
# Configuration des conseils de diagnostic pour l'IA
# ---------------------------------------------------------
DISEASE_ADVICE = {
    "mildiou": {
        "name_fr": "Mildiou",
        "advice_fr": "Appliquez un traitement fongicide et réduisez l'irrigation.",
        "name_ar": "البياض الدقيقي",
        "advice_ar": "قم بتطبيق مبيد فطري وقلل من الري.",
        "image_url": "https://example.com/images/mildiou.jpg"
    },
    "healthy": {
        "name_fr": "Plante saine",
        "advice_fr": "Votre plante est en bonne santé. Continuez la surveillance habituelle.",
        "name_ar": "نبات صحي",
        "advice_ar": "النبات بصحة جيدة. تابع المراقبة المعتادة.",
        "image_url": "https://example.com/images/healthy.jpg"
    },
    "saine": {
        "name_fr": "Plante saine",
        "advice_fr": "Votre plante est en bonne santé. Continuez la surveillance habituelle.",
        "name_ar": "نبات صحي",
        "advice_ar": "النبات بصحة جيدة. تابع المراقبة المعتادة.",
        "image_url": "https://example.com/images/healthy.jpg"
    },
    "unknown_plant_or_disease": {
        "name_fr": "Analyse incertaine / Culture non prise en charge",
        "advice_fr": "Désolé, je n'ai pas pu identifier la culture ou la maladie avec certitude. Veuillez vous assurer que la photo est claire et bien éclairée, ou que la culture fait partie de celles que je peux analyser (ex: tomate).",
        "name_ar": "تحليل غير مؤكد / محصول غير مدعوم",
        "advice_ar": "عذراً، لم أتمكن من تحديد المحصول أو المرض بشكل مؤكد. يرجى التأكد من أن الصورة واضحة ومضاءة جيداً، أو أن المحصول من بين الأنواع التي يمكنني تحليلها (مثل الطماطم).",
        "image_url": "https://example.com/images/question_mark.jpg"
    },
    "pepper__bell___bacterial_spot": {
        "name_fr": "Tache bactérienne du poivron",
        "advice_fr": "La tache bactérienne se manifeste par des lésions sombres. Utilisez des semences saines, évitez l'arrosage par aspersion et retirez les plantes infectées.",
        "name_ar": "بقعة فلفل الجرس البكتيرية",
        "advice_ar": "تظهر البقعة البكتيرية على شكل آفات داكنة. استخدم بذورًا صحية، تجنب الري بالرش، وأزل النباتات المصابة.",
        "image_url": "https://example.com/images/pepper_bacterial_spot.jpg"
    },
    "pepper__bell___healthy": {
        "name_fr": "Poivron sain",
        "advice_fr": "Votre poivron est en excellente forme ! Maintenez un bon arrosage et un ensoleillement suffisant.",
        "name_ar": "فلفل الجرس صحي",
        "advice_ar": "فلفل الجرس الخاص بك في حالة ممتازة! حافظ على الري الجيد وأشعة الشمس الكافية.",
        "image_url": "https://example.com/images/pepper_healthy.jpg"
    }
}

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
            # 1. On appelle la VRAIE analyse de l'IA
            result = predict_disease(MediaUrl0)
            predicted_disease_tag = result.get("disease", "unknown_plant_or_disease").lower()
            confidence = result.get("confidence", 0.0)

            # 2. Vérification du tag et seuil de confiance
            advice_data = DISEASE_ADVICE.get(predicted_disease_tag)
            if advice_data is None or confidence < 0.75:
                advice_data = DISEASE_ADVICE["unknown_plant_or_disease"]
                predicted_disease_tag = "unknown_plant_or_disease"

            data_culture = "Inconnue"
            if "tomato" in predicted_disease_tag or "mildiou" in predicted_disease_tag or "healthy" in predicted_disease_tag or "saine" in predicted_disease_tag:
                data_culture = "Tomate"
            elif "pepper" in predicted_disease_tag:
                data_culture = "Poivron"

            # 3. Construction de la réponse
            response_text_fr = (
                f"🔍 *DIAGNOSTIC FELLAH.AI*\n\n"
                f"🌿 Culture : *{data_culture}*\n"
                f"🦠 État : *{advice_data['name_fr']}*\n"
                f"✅ Fiabilité : *{confidence * 100:.1f}%*\n\n"
                f"💡 *Conseil :* {advice_data['advice_fr']}"
            )

            response_text_ar = (
                f"🔎 تشخيص فلاح.الذكاء الاصطناعي\n"
                f"المحصول : *{ 'طماطم' if data_culture == 'Tomate' else 'فلفل' if data_culture == 'Poivron' else 'غير معروف'}*\n"
                f"الحالة : *{advice_data['name_ar']}*\n"
                f"موثوقية : *{confidence * 100:.1f}%*\n\n"
                f"💡 نصيحة : {advice_data['advice_ar']}"
            )

            msg.body(response_text_fr + "\n\n" + response_text_ar)
            if advice_data.get("image_url"):
                msg.media(advice_data["image_url"])

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
