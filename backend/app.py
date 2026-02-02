from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os, uuid, json, re, time, base64, hmac, hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")
# CORS(app, resources={r"/*": {"origins": "*"}})
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500", "https://zoom-ai-interviewer-production.up.railway.app/", "https://zoom-ai-interviewer-production.up.railway.app/"])

# 🔥 ULTIMATE CORS CONFIGURATION
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# -------------------- CONFIG --------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ZOOM_SDK_KEY = os.getenv("ZOOM_SDK_KEY")
ZOOM_SDK_SECRET = os.getenv("ZOOM_SDK_SECRET")

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None
active_interviews = {}

WORKING_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768"
]

# -------------------- UTILS --------------------
def safe_groq_call(prompt):
    if not client:
        return None

    for model in WORKING_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            content = response.choices[0].message.content
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            continue
    return None

# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/ai-interviewer")
def ai_interviewer():
    return send_from_directory("static", "ai-interviewer.html")

# -------------------- QUESTIONS --------------------
@app.route("/api/generate-questions", methods=["POST"])
def generate_questions():
    data = request.json or {}
    jd = data.get("jobDescription", "")
    resume = data.get("resumeText", "")

    prompt = f"""
Job: {jd}
Resume: {resume}

Generate 6 interview questions.
Return JSON:
{{"questions":[{{"id":1,"text":"question","category":"technical"}}]}}
"""

    result = safe_groq_call(prompt)
    if result and "questions" in result:
        return jsonify(result)

    fallback = [
        {"id":1,"text":"Tell me about your React experience.","category":"technical"},
        {"id":2,"text":"Explain a challenging deployment.","category":"technical"},
        {"id":3,"text":"How do you optimize performance?","category":"technical"},
        {"id":4,"text":"Describe CI/CD you’ve used.","category":"technical"},
        {"id":5,"text":"How do you handle deadlines?","category":"behavioral"},
        {"id":6,"text":"How do you review code?","category":"behavioral"},
    ]
    return jsonify({"questions": fallback})

# -------------------- INTERVIEW --------------------
@app.route("/api/create-interview", methods=["POST"])
def create_interview():
    data = request.json
    interview_id = str(uuid.uuid4())[:8].upper()

    active_interviews[interview_id] = {
        "id": interview_id,
        "candidate": data["candidateName"],
        "questions": data["questions"],
        "current_question": 0,
        "transcripts": []
    }

    return jsonify({"interviewId": interview_id})

# -------------------- ZOOM --------------------
def get_zoom_token():
    url = "https://zoom.us/oauth/token"
    auth = base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    data = {"grant_type": "account_credentials", "account_id": ZOOM_ACCOUNT_ID}
    r = requests.post(url, headers=headers, data=data)
    return r.json().get("access_token")

# @app.route("/api/create-zoom-meeting/<interview_id>/<candidate>")
# def create_zoom(interview_id, candidate):
#     token = get_zoom_token()
#     if not token:
#         return jsonify({"error": "Zoom auth failed"}), 500

#     payload = {
#         "topic": f"AI Interview - {candidate}",
#         "type": 1,
#         "settings": {
#             "auto_recording": "cloud",
#             "waiting_room": False
#         }
#     }

#     r = requests.post(
#         "https://api.zoom.us/v2/users/me/meetings",
#         headers={"Authorization": f"Bearer {token}"},
#         json=payload
#     )
    
#     zoom_info = {
#                 "meeting_id": str(meeting.get("id", "")),
#                 "join_url": meeting.get("join_url", ""),                    # Candidate joins here
#                 "start_url": meeting.get("start_url", ""),                  # AI bot auto-starts meeting
#                 "password": meeting.get("password", ""),
#                 "candidate_name": candidate_name,
#                 "interview_id": interview_id,
                
#                 # AI Bot Configuration
#                 "ai_bot_config": {
#                     "bot_name": f"AI_Interviewer_{interview_id}",
#                     "bot_role": "interviewer",
#                     "auto_join": True,
#                     "auto_start_meeting": True,
#                     "interview_script_id": interview_id,
#                     "llm_model": "gpt-4o",  # or grok, gemini
#                     "max_questions": 15
#                 },
                
#                 # Recording Settings (Cloud + Local)
#                 "recording_active": True,
#                 "recording_config": {
#                     "cloud_recording": True,
#                     "local_recording": False,
#                     "auto_start_recording": True,
#                     "recording_layout": "speaker_view",
#                     "file_retention_days": 90
#                 },
                
#                 # Transcription Settings
#                 "transcript_enabled": True,
#                 "transcription_config": {
#                     "auto_transcribe": True,
#                     "language": "en-US",
#                     "speaker_identification": True,
#                     "real_time_transcript": True,
#                     "diarization": True,  # Separate speakers (AI vs Candidate)
#                     "custom_vocabulary": [candidate_name, "resume", "experience"],  # Boost accuracy
#                     "output_formats": ["txt", "srt", "json"]
#                 },
                
#                 # Interview Automation
#                 "interview_automation": {
#                     "duration_minutes": 30,
#                     "auto_end_meeting": True,
#                     "questions_per_minute": 2,
#                     "skill_assessment": True,
#                     "sentiment_analysis": True
#                 },
                
#                 # Zoom Meeting Settings
#                 "meeting_settings": {
#                     "host_video": False,  # AI bot controls video
#                     "participant_video": True,
#                     "audio_enabled": True,
#                     "mute_participants_on_entry": False,
#                     "waiting_room": False,  # Direct entry for AI automation
#                     "meeting_type": "scheduled"
#                 }
#             }

#     meeting = r.json()
#     # active_interviews[interview_id]["zoom"] = meeting
#     active_interviews[interview_id] = active_interviews.get(interview_id, {})
#     active_interviews[interview_id].update({
#     "candidate": candidate,
#     "zoom": zoom  # or meeting depending on your code
#     })
#     return jsonify(meeting)

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


# -------------------- AI FLOW --------------------
@app.route("/api/ai/next-question/<interview_id>", methods=["POST"])
def ai_next_question(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return jsonify({"error": "Invalid interview"}), 404

    data = request.json or {}
    answer = data.get("answer", "")

    session["transcripts"].append({
        "question": session["questions"][session["current_question"]]["text"],
        "answer": answer
    })

    session["current_question"] += 1

    if session["current_question"] >= len(session["questions"]):
        return jsonify({"done": True})

    return jsonify({
        "done": False,
        "question": session["questions"][session["current_question"]]["text"]
    })

# -------------------- ZOOM SDK SIGNATURE --------------------
@app.route("/api/zoom-signature", methods=["POST"])
def zoom_signature():
    data = request.json
    meeting_number = data["meetingNumber"]
    role = 0

    ts = int(time.time() * 1000) - 30000
    msg = f"{ZOOM_SDK_KEY}{meeting_number}{ts}{role}"
    hash = hmac.new(ZOOM_SDK_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(
        f"{ZOOM_SDK_KEY}.{meeting_number}.{ts}.{role}.{base64.b64encode(hash).decode()}".encode()
    ).decode()

    return jsonify({"signature": signature})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
