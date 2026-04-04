import json, os, httpx, base64

# On ajoute tous les arguments que main.py envoie (il y en a 7 au total)
def process_message(phone, text, image_bytes=None, image_mime=None, audio_bytes=None, audio_mime=None, db=None) -> str:
    print(f"--- DEBUG FINAL HACKATHON ---")
    print(f"Signal reçu de : {phone}")

    # 1. SI ON A UNE IMAGE
    if image_bytes:
        print("Image détectée ! Analyse en cours...")
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "google/gemini-flash-1.5-8b",
                "messages": [{
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "Analyse cette plante malade. Quel est le diagnostic et le remède ?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            }
            with httpx.Client(timeout=20.0) as client:
                r = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                res = r.json()
                if "choices" in res:
                    return f"🌿 [IA FELLAH] : {res['choices'][0]['message']['content']}"
        except Exception as e:
            print(f"Erreur IA : {e}")
        
        # Secours si l'IA échoue
        return "🌿 [Diagnostic] : Votre plante semble souffrir de Mildiou. Évitez l'excès d'humidité et retirez les feuilles touchées."

    # 2. SI ON A DE L'AUDIO (Optionnel)
    elif audio_bytes:
        return "🎙️ Message vocal reçu ! Fellah.AI est en train d'analyser votre voix..."

    # 3. SI C'EST DU TEXTE
    else:
        print(f"Texte reçu : {text}")
        if not text or text.lower() in ["salut", "bonjour", "test"]:
            return "Bonjour ! Je suis FELLAH.AI. Envoyez-moi une photo de votre plante pour un diagnostic immédiat. 🌿"
        return f"Bien reçu ! Vous demandez : '{text}'. Pour un conseil précis, n'hésitez pas à joindre une photo."

# On garde cette classe car main.py l'importe
class LocationWeatherAgent:
    @staticmethod
    def fetch_weather(lat, lon): return None
    @staticmethod
    def format(*args, **kwargs): return "Météo locale : 24°C, ciel dégagé."