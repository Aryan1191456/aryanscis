# =============================
# JARVIS – OPTIMIZED FAST VERSION (WITH AUTO MEMORY)
# Hinglish | Voice | Weather | Web Search | Memory
# =============================

from dotenv import load_dotenv
import os
from datetime import datetime
import requests
import json
from openai import OpenAI

import speech_recognition as sr
import edge_tts
import asyncio
import tempfile
import playsound

# -----------------------------
# SETUP
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

VOICE_NAME = "en-IN-PrabhatNeural"
MEMORY_FILE = "memory.json"

SEARCH_KEYWORDS = [
    "what", "who", "when", "where", "how", "search",
    "kya", "kaun", "kab", "kaise", "kahan",
    "batao", "bataiye", "jankari", "details", "history"
]

# -----------------------------
# MEMORY SYSTEM
# -----------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

memory = load_memory()

# -----------------------------
# AUTO MEMORY EXTRACTOR (IMPORTANT)
# -----------------------------
def auto_memory_extractor(text):
    t = text.lower()

    # NAME
    if "my name is" in t:
        name = t.replace("my name is", "").strip().title()
        memory["name"] = name
        save_memory(memory)
        return f"Okay sir, mujhe yaad rahega, aapka naam {name} hai."

    # EDUCATION
    if "read in class" in t or "study in class" in t:
        words = t.split()
        for i, w in enumerate(words):
            if w == "class" and i + 1 < len(words):
                edu = f"class {words[i + 1]}"
                memory["education"] = edu
                save_memory(memory)
                return f"Theek hai sir, mujhe yaad rahega, aap {edu} me padhte hain."

    # LIKES
    if "i like" in t or "i love" in t:
        item = t.replace("i like", "").replace("i love", "").strip()
        memory.setdefault("likes", []).append(item)
        save_memory(memory)
        return f"Samajh gaya sir, aapko {item} pasand hai."

    # DISLIKES
    if "i hate" in t or "i don't like" in t:
        item = t.replace("i hate", "").replace("i don't like", "").strip()
        memory.setdefault("dislikes", []).append(item)
        save_memory(memory)
        return f"Theek hai sir, mujhe yaad rahega, aapko {item} pasand nahi hai."

    return None

# -----------------------------
# SPEAK
# -----------------------------
async def speak(text):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            path = f.name
        communicate = edge_tts.Communicate(text, voice=VOICE_NAME, rate="+12%")
        await communicate.save(path)
        playsound.playsound(path)
    except Exception as e:
        print("TTS Error:", e)

# -----------------------------
# WEATHER
# -----------------------------
def get_weather(city):
    try:
        data = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=4
        ).json()
        if data.get("cod") != 200:
            return None
        return f"{city} me temperature {data['main']['temp']} degree Celsius hai."
    except:
        return None

def get_weather_fallback(city):
    try:
        geo = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1",
            timeout=4
        ).json()
        if not geo.get("results"):
            return "City samajh nahi aaya."
        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]
        weather = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
            timeout=4
        ).json()["current_weather"]
        return f"{city} me temperature {weather['temperature']} degree Celsius hai."
    except:
        return "Weather service available nahi hai."

# -----------------------------
# GOOGLE SEARCH
# -----------------------------
def google_search(query):
    try:
        data = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_SEARCH_API_KEY,
                "cx": GOOGLE_SEARCH_ENGINE_ID,
                "q": query,
                "num": 2
            },
            timeout=4
        ).json()
        if not data.get("items"):
            return None
        return " ".join(item["snippet"] for item in data["items"])
    except:
        return None

# -----------------------------
# COMMAND HANDLER
# -----------------------------
def handle_command(text):
    t = text.lower()

    if t in ["hi", "hello", "hey"]:
        return "Hello sir, main Jarvis hoon."

    if "time" in t:
        return datetime.now().strftime("Abhi time %I:%M %p hai.")

    if "date" in t:
        return datetime.now().strftime("Aaj ki date %d %B %Y hai.")

    if "who made you" in t or "kisne banaya" in t:
        return "Mujhe Aryan ne design aur program kiya hai, sir."

    if "where do i read" in t or "where i read" in t:
        edu = memory.get("education")
        return f"Sir, aap {edu} me padhte hain." if edu else "Sir, aapne apni class nahi batayi."

    if "weather" in t or "mausam" in t:
        city = t.split()[-1]
        return get_weather(city) or get_weather_fallback(city)

    if t.startswith("search "):
        query = text.replace("search", "").strip()
        return google_search(query) or "Is topic par direct result nahi mila."

    if any(word in t.split() for word in SEARCH_KEYWORDS):
        result = google_search(text)
        if result:
            return result

    return None

# -----------------------------
# AI RESPONSE
# -----------------------------
def ask_ai(text):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Reply briefly in Hinglish using English letters only."},
            {"role": "user", "content": text}
        ],
        temperature=0.6
    )
    return res.choices[0].message.content.strip()

# -----------------------------
# MIC INPUT
# -----------------------------
def listen_mic():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
    try:
        text = r.recognize_google(audio, language="en-IN")
        print("You:", text)
        return text
    except:
        return ""

# -----------------------------
# MAIN LOOP
# -----------------------------
print("Jarvis is online. Say 'exit' to stop.\n")

while True:
    user_input = listen_mic()
    if not user_input:
        continue

    if user_input.lower() == "exit":
        asyncio.run(speak("Bye sir, phir milte hain."))
        break

    # AUTO MEMORY FIRST
    memory_reply = auto_memory_extractor(user_input)
    if memory_reply:
        print("Jarvis:", memory_reply)
        asyncio.run(speak(memory_reply))
        continue

    result = handle_command(user_input)

    if result:
        print("Jarvis:", result)
        asyncio.run(speak(result))
    else:
        reply = ask_ai(user_input)
        print("Jarvis:", reply)
        asyncio.run(speak(reply))
