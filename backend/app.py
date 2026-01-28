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

load_dotenv()
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500", "https://zoom-ai-interviewer-production.up.railway.app/", "https://zoom-ai-interviewer-production.up.railway.app/"])

# 🔥 ULTIMATE CORS CONFIGURATION
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# ✅ WORKING MODELS (Jan 2026) - Multiple fallbacks
WORKING_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192", 
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768"
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None

if GROQ_API_KEY:
    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    print("✅ GROQ client initialized")

client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1") if os.getenv("GROQ_API_KEY") else None
active_interviews = {}

def safe_groq_call(prompt, max_retries=2):
    print("""✅ BULLETPROOF Groq API call with ALL error handling""")
    print(f"Client : {client}")
    if not client:
        return None
    
    for model in WORKING_MODELS:
        try:
            print(f"🔄 Trying model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Return ONLY valid JSON: {\"questions\": [{\"id\":1,\"text\":\"question\",\"category\":\"technical\"}]} NO markdown, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            # ✅ FIXED: SAFE response parsing
            if (hasattr(response, 'choices') and 
                isinstance(response.choices, list) and 
                len(response.choices) > 0 and 
                hasattr(response.choices[0], 'message') and 
                hasattr(response.choices[0].message, 'content')):
                
                content = response.choices[0].message.content.strip()
                print(f"✅ SUCCESS with {model}: {content[:60]}...")
                
                # Extract JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        questions = result.get('questions', [])
                        if questions:
                            return questions
                    except json.JSONDecodeError:
                        pass
            
        except Exception as e:
            print(f"❌ {model} failed: {str(e)[:80]}")
            continue
    
    return None

# Safe imports with fallbacks
try:
    from openai import OpenAI
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

@app.route('/api/health')
def health():
    return jsonify({
        "status": "Zoom AI Interviewer LIVE ✅",
        "openai": HAS_OPENAI,
        "port": os.getenv('PORT', 5000)
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app - handles all frontend routes"""
    static_path = app.static_folder
    if path != "" and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(static_path, 'index.html')

@app.route('/api/generate-questions', methods=['POST', 'OPTIONS'])
def generate_questions():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    data = request.get_json() or {}
    job_description = data.get('jobDescription', '').strip()
    resume_text = data.get('resumeText', '').strip()
    
    print(f"📥 JD: {job_description[:60]}...")
    
    if not job_description:
        return jsonify({"error": "Job description required"}), 400
    
    # Try Groq first
    prompt = f"""Job: {job_description}
Resume: {resume_text or 'None'}

Generate 6 targeted interview questions. Return ONLY JSON."""
    
    questions = safe_groq_call(prompt)
    print(f"AI questions : {questions}")
    if questions: 
        print(f"✅ Generated {len(questions)} AI questions")
        return jsonify({"questions": questions})
    
    # ✅ SMART FALLBACK - No errors, always works
    print("🔄 Using smart fallback")
    words = [w for w in job_description.lower().split() if len(w) > 3]
    tech_terms = words[:3]
    
    fallback = [
        {"id": 1, "text": f"Can you describe your experience with {tech_terms[0] if tech_terms else 'the core technology stack'}?", "category": "technical"},
        {"id": 2, "text": "Tell me about your most challenging project and your specific role in it", "category": "behavioral"},
        {"id": 3, "text": "How do you approach performance optimization in production applications?", "category": "technical"},
        {"id": 4, "text": "Walk me through your typical deployment and CI/CD process", "category": "technical"},
        {"id": 5, "text": "Describe a time you had to learn a new technology under pressure", "category": "behavioral"},
        {"id": 6, "text": "How do you handle code reviews and collaborate with other developers?", "category": "technical"}
    ]
    
    return jsonify({"questions": fallback})

# ✅ PERSISTENT STORAGE
INTERVIEWS_FILE = "interviews.json"

def load_interviews():
    """Load interviews from file"""
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
            print(f"✅ Loaded {len(active_interviews)} interviews")
        except:
            print("⚠️ Corrupted interviews file, starting fresh")

def save_interviews():
    """Save interviews to file"""
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save failed: {e}")

# ✅ LOAD ON STARTUP
load_interviews()

@app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
def create_interview():
    if request.method == 'OPTIONS':
        print("✅ OPTIONS request handled")
        return jsonify({"status": "ok"}), 200
    
    print("✅ POST /api/create-interview HIT!")
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
    
    print(f"🎤 Interview {interview_id} created!")
    return jsonify({
        "interviewId": interview_id,
        "joinUrl": f"/create-zoom-meeting/{interview_id}/{candidate_name.replace(' ', '-')}"
    })

@app.route('/api/create-zoom-meeting/<interview_id>/<candidate_name>', methods=['POST', 'OPTIONS'])
def create_zoom_meeting(interview_id, candidate_name):
    """
    ✅ FIXED: Works with BOTH interview_id AND candidate_name in URL
    Usage: POST /api/create-zoom-meeting/ABC123/John-Doe
    """
    print(f"🎯 Creating Zoom: {interview_id} for {candidate_name}")
    
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    # Clean candidate name (URL safe)
    candidate_name = candidate_name.replace('-', ' ').replace('_', ' ').title()
    
    # 1. Get Zoom token
    token = get_zoom_token()
    print(f"🔑 Zoom token: {'✅ YES' if token else '❌ NO'}")
    
    if not token:
        print("⚠️ Zoom unavailable - DEMO MODE")
        return jsonify({
            "meeting_id": f"DEMO-{interview_id}",
            "join_url": f"http://localhost:5000/interview/{interview_id}/{candidate_name.replace(' ', '-')}",
            "password": "demo",
            "candidate_name": candidate_name,
            "recording_active": False,
            "demo_mode": True
        })
    
    # 2. Create REAL Zoom meeting
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "topic": f"🤖 AI Interview: {candidate_name} [{interview_id}]",
        "type": 1,  # Instant meeting - starts NOW
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",        # 🔥 Otter.ai recording
            "waiting_room": True,             # Candidate waits for AI
            "host_save_recording": "cloud_only",
            "cloud_recording": {
                "status": "on",
                "type": "audio_transcript_video"  # Video + Transcript
            }
        }
    }
    
    try:
        print(f"📹 Creating Zoom meeting for {candidate_name}...")
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 201:
            meeting = response.json()
            # zoom_info = {
            #     "meeting_id": str(meeting.get("id", "")),
            #     "join_url": meeting.get("join_url", ""),
            #     "start_url": meeting.get("start_url", ""),  # For AI bot
            #     "password": meeting.get("password", ""),
            #     "candidate_name": candidate_name,
            #     "interview_id": interview_id,
            #     "recording_active": True,
            #     "transcript_enabled": True
            # }
            zoom_info = {
    "meeting_id": str(meeting.get("id", "")),
    "join_url": meeting.get("join_url", ""),                    # Candidate joins here
    "start_url": meeting.get("start_url", ""),                  # AI bot auto-starts meeting
    "password": meeting.get("password", ""),
    "candidate_name": candidate_name,
    "interview_id": interview_id,
    
    # AI Bot Configuration
    "ai_bot_config": {
        "bot_name": f"AI_Interviewer_{interview_id}",
        "bot_role": "interviewer",
        "auto_join": True,
        "auto_start_meeting": True,
        "interview_script_id": interview_id,
        "llm_model": "gpt-4o",  # or grok, gemini
        "max_questions": 15
    },
    
    # Recording Settings (Cloud + Local)
    "recording_active": True,
    "recording_config": {
        "cloud_recording": True,
        "local_recording": False,
        "auto_start_recording": True,
        "recording_layout": "speaker_view",
        "file_retention_days": 90
    },
    
    # Transcription Settings
    "transcript_enabled": True,
    "transcription_config": {
        "auto_transcribe": True,
        "language": "en-US",
        "speaker_identification": True,
        "real_time_transcript": True,
        "diarization": True,  # Separate speakers (AI vs Candidate)
        "custom_vocabulary": [candidate_name, "resume", "experience"],  # Boost accuracy
        "output_formats": ["txt", "srt", "json"]
    },
    
    # Interview Automation
    "interview_automation": {
        "duration_minutes": 30,
        "auto_end_meeting": True,
        "questions_per_minute": 2,
        "skill_assessment": True,
        "sentiment_analysis": True
    },
    
    # Zoom Meeting Settings
    "meeting_settings": {
        "host_video": False,  # AI bot controls video
        "participant_video": True,
        "audio_enabled": True,
        "mute_participants_on_entry": False,
        "waiting_room": False,  # Direct entry for AI automation
        "meeting_type": "scheduled"
    }
}

            
            # Save to session
            active_interviews[interview_id] = active_interviews.get(interview_id, {})
            active_interviews[interview_id].update({
                "candidate": candidate_name,
                "zoom": zoom_info
            })
            
            print(f"✅ ZOOM LIVE: https://zoom.us/j/{meeting.get('id')}")
            return jsonify(zoom_info)
            
        else:
            print(f"❌ Zoom API failed: {response.text}")
            return jsonify({
                "error": response.json().get("message", "Zoom API error"),
                "status_code": response.status_code,
                "demo_url": f"http://localhost:5000/interview/{interview_id}/{candidate_name.replace(' ', '-')}"
            })
            
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        return jsonify({
            "error": str(e),
            "demo_url": f"http://localhost:5000/interview/{interview_id}/{candidate_name.replace(' ', '-')}"
        })


def get_zoom_token():
    """Server-to-Server OAuth (Required for production)"""
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
        token_data = response.json()
        
        if response.status_code == 200:
            print("✅ Zoom token acquired")
            return token_data.get("access_token")
        else:
            print(f"❌ Zoom token failed: {token_data}")
            return None
            
    except Exception as e:
        print(f"❌ Token error: {e}")
        return None

@app.route('/api/next-question/<interview_id>', methods=['POST'])
def next_question(interview_id):
    """Advance to next question"""
    session = active_interviews.get(interview_id)
    if session:
        session['current_question'] += 1
        save_interviews()
        print(f"➡️ {interview_id}: Q{session['current_question']}")
    return jsonify({"status": "next"})

# Zoom recording webhook (optional)
@app.route('/api/zoom-recording', methods=['POST'])
def zoom_recording_webhook():
    data = request.json
    print("📹 Zoom recording complete:", data)
    return jsonify({"status": "received"})

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

def get_zoom_access_token():
    """Get Server-to-Server OAuth token"""
    url = f"https://zoom.us/oauth/token"
    headers = {"Authorization": f"Basic {base64.b64encode(f'{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}'.encode()).decode()}"}
    data = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json()["access_token"]


@app.route('/api/submit-answer/<interview_id>', methods=['POST', 'OPTIONS'])
def submit_answer(interview_id):
    print(f"Enter Sumbmit Answer")
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    session = active_interviews.get(interview_id)
    if session:
        print(f"Submit Answer check Session : {session}")
        if 'answers' not in session:
            session['answers'] = []
        video_file = request.files.get('video')  # ✅ Changed from 'audio' to 'video'
        if video_file:
            print(f"Submit Answer check video file : {video_file}")
            os.makedirs("recordings", exist_ok=True)
            filename = video_file.filename
            filepath = f"recordings/{filename}"
            video_file.save(filepath)
            
            session['answers'].append({
                'question_id': session['current_question'] + 1,
                'filename': filename,
                'type': 'video'
            })
            session['current_question'] += 1
            save_interviews()
            
            print(f"✅ Saved VIDEO: {filename}")
    
    return jsonify({"status": "saved"})


@app.route('/api/tts-question/<int:qid>')
def tts_question(qid):
    text = request.args.get('text', 'Please answer this question.')
    try:
        from gtts import gTTS
        import io
        tts = gTTS(text=text[:200], lang='en')
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return send_file(buffer, mimetype='audio/mpeg')
    except:
        return "TTS unavailable", 500


if __name__ == '__main__':
    print("🚀 Backend running on http://localhost:5000")
    app.run(port=5000, debug=True)

@app.route('/debug')
def debug():
    """🔍 DEBUG - Check active interviews"""
    return jsonify({
        "active_interviews": list(active_interviews.keys()),
        "count": len(active_interviews)
    })