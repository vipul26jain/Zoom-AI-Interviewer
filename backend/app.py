from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import json
import re
import requests
import base64
import threading
import time
from datetime import datetime
import io
from gtts import gTTS  # pip install gtts

load_dotenv()
app = Flask(__name__)

# 🔥 ULTIMATE CORS (allows all origins for testing)
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# ✅ WORKING GROQ MODELS (2026)
WORKING_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192", 
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768"
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# 🔥 PERSISTENT STORAGE
active_interviews = {}
INTERVIEWS_FILE = "interviews.json"

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

# 🔥 ZOOM AI BOT MANAGER (NO SELENIUM!)
class ZoomAIBot:
    def __init__(self, app):
        self.app = app
        self.active_bots = {}
        
    def start_interview_bot(self, interview_id, zoom_info):
        """🤖 Launch server-side AI bot"""
        print(f"🤖 Starting AI Bot for {interview_id}")
        
        # 1. Auto-start meeting via Zoom API
        if self.auto_start_meeting(zoom_info["meeting_id"]):
            print(f"✅ Meeting auto-started: {zoom_info['meeting_id']}")
        
        # 2. Launch AI interview in background thread
        bot_thread = threading.Thread(
            target=self.run_ai_interview,
            args=(interview_id, zoom_info),
            daemon=True
        )
        bot_thread.start()
        
        self.active_bots[interview_id] = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "zoom_info": zoom_info
        }
        return {"bot_status": "launched"}
    
    def auto_start_meeting(self, meeting_id):
        """🚀 Start meeting via Zoom API"""
        token = get_zoom_token()
        if not token:
            return False
            
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"status": "started"}
        
        try:
            response = requests.put(url, headers=headers, json=data)
            return response.status_code in [204, 200]
        except:
            return False
    
    def run_ai_interview(self, interview_id, zoom_info):
        """🎤 Execute full AI interview"""
        session = active_interviews.get(interview_id)
        if not session:
            return
        
        questions = session.get('questions', [])
        print(f"🎯 Starting {len(questions)} questions for {zoom_info['candidate_name']}")
        
        for q_idx, question in enumerate(questions[:10]):  # Max 10 questions
            print(f"🤖 Q{q_idx+1}: {question['text']}")
            
            # Simulate sending question (chat API would go here)
            time.sleep(3)
            
            # Simulate waiting for response (30s timeout)
            response = self.simulate_candidate_response()
            
            # AI Analysis
            analysis = self.analyze_response(question['text'], response)
            
            # Save answer
            if 'answers' not in session:
                session['answers'] = []
            session['answers'].append({
                'question_id': question['id'],
                'question': question['text'],
                'response': response,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            save_interviews()
            
            time.sleep(15)  # 15s between questions
        
        # End interview
        self.end_meeting(zoom_info["meeting_id"])
        print(f"🏁 Interview COMPLETE: {interview_id}")
    
    def simulate_candidate_response(self):
        """🎧 Mock candidate response (replace with real transcript)"""
        return "I have 3 years experience with React and Node.js..."
    
    def analyze_response(self, question, response):
        """🧠 AI analyze answer"""
        if not client:
            return "Analysis unavailable (no Groq key)"
        
        try:
            resp = client.chat.completions.create(
                model=WORKING_MODELS[0],
                messages=[{
                    "role": "user", 
                    "content": f"Score 1-10: Q: {question}\nA: {response}\nReturn just the score."
                }],
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except:
            return "Error analyzing"
    
    def end_meeting(self, meeting_id):
        """🔚 End meeting"""
        token = get_zoom_token()
        if token:
            url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
            headers = {"Authorization": f"Bearer {token}"}
            data = {"status": "ended"}
            requests.put(url, headers=headers, json=data)

# Initialize
ai_bot_manager = ZoomAIBot(app)

def save_interviews():
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save failed: {e}")

def load_interviews():
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
        except:
            pass

def get_zoom_token():
    """🔑 Server-to-Server OAuth"""
    if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
        return None
        
    try:
        url = "https://zoom.us/oauth/token"
        auth = base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "account_credentials",
            "account_id": ZOOM_ACCOUNT_ID
        }
        
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
    except:
        pass
    return None

def safe_groq_call(prompt):
    """🤖 Safe Groq API call"""
    if not client:
        return None
    
    for model in WORKING_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON: {\"questions\": [{\"id\":1,\"text\":\"question\",\"category\":\"technical\"}]}"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group()).get('questions', [])
        except:
            continue
    return None

# 🔥 ROUTES
@app.route('/api/health')
def health():
    return jsonify({
        "status": "🚀 Zoom AI Interviewer LIVE",
        "zoom_ready": bool(get_zoom_token()),
        "groq_ready": bool(client),
        "active_interviews": len(active_interviews)
    })

@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    data = request.get_json() or {}
    job_description = data.get('jobDescription', '')
    
    prompt = f"Job: {job_description}\nGenerate 6 targeted interview questions. Return ONLY JSON."
    questions = safe_groq_call(prompt)
    
    if questions:
        return jsonify({"questions": questions})
    
    # Fallback
    return jsonify({"questions": [
        {"id": 1, "text": "Describe your experience with React", "category": "technical"},
        {"id": 2, "text": "Most challenging project?", "category": "behavioral"},
        {"id": 3, "text": "Performance optimization approach?", "category": "technical"}
    ]})

@app.route('/api/create-interview', methods=['POST'])
def create_interview():
    data = request.get_json() or {}
    questions = data.get('questions', [])
    candidate_name = data.get('candidateName', 'Candidate')
    
    interview_id = str(uuid.uuid4())[:8].upper()
    active_interviews[interview_id] = {
        'id': interview_id,
        'candidate': candidate_name,
        'questions': questions,
        'current_question': 0
    }
    save_interviews()
    
    return jsonify({
        "interviewId": interview_id,
        "createZoomUrl": f"/api/create-zoom-meeting/{interview_id}/{candidate_name.replace(' ', '-')}"
    })

@app.route('/api/create-zoom-meeting/<interview_id>/<candidate_name>', methods=['POST'])
def create_zoom_meeting(interview_id, candidate_name):
    candidate_name = candidate_name.replace('-', ' ').title()
    
    # Create Zoom meeting
    token = get_zoom_token()
    if not token:
        return jsonify({
            "demo_mode": True,
            "join_url": f"http://localhost:5000/interview/{interview_id}/{candidate_name.replace(' ', '-')}",
            "interview_id": interview_id
        })
    
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "topic": f"🤖 AI Interview: {candidate_name} [{interview_id}]",
        "type": 1,  # Instant
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",
            "waiting_room": False,
            "join_before_host": True,
            "mute_upon_entry": False
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 201:
        return jsonify({"error": "Zoom creation failed", "demo": True})
    
    meeting = response.json()
    zoom_info = {
        "meeting_id": str(meeting.get("id")),
        "join_url": meeting.get("join_url"),
        "start_url": meeting.get("start_url"),
        "password": meeting.get("password"),
        "candidate_name": candidate_name,
        "interview_id": interview_id
    }
    
    # 🔥 AUTO-START AI BOT!
    ai_bot_manager.start_interview_bot(interview_id, zoom_info)
    
    # Save
    active_interviews[interview_id]["zoom"] = zoom_info
    save_interviews()
    
    return jsonify({
        "success": True,
        "zoom_info": zoom_info,
        "ai_bot": "auto_started",
        "candidate_join": meeting.get("join_url")
    })

@app.route('/api/interviews')
def list_interviews():
    return jsonify({"interviews": list(active_interviews.values())})

@app.route('/debug')
def debug():
    return jsonify(active_interviews)

# Static file serving for React
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(f"static/{path}"):
        return send_from_directory("static", path)
    return send_from_directory("static", 'index.html')

if __name__ == '__main__':
    load_interviews()
    print("🚀 Zoom AI Interviewer starting on http://localhost:5000")
    app.run(port=int(os.getenv('PORT', 5000)), debug=True)
