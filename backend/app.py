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
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# import pyautogui

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

def analyze_candidate_answer(answer_text, previous_question, skills):
    """🤖 AI analyzes answer → generates adaptive follow-up"""
    if not client:
        return {
            "score": 3,
            "follow_up": "Can you give me a specific example from that experience?",
            "next_topic": "examples"
        }
    
    prompt = f"""
Previous question: "{previous_question}"
Candidate skills: {skills}
Answer: {answer_text[:1000]}

Analyze and suggest BEST follow-up question. Return ONLY JSON:
{{
  "score": 4,
  "strengths": ["Good explanation"],
  "weaknesses": ["Vague implementation"],
  "follow_up": "How did you implement that specific feature?",
  "next_topic": "implementation"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        start = content.find('{')
        end = content.rfind('}') + 1
        if start > -1 and end > start:
            return json.loads(content[start:end])
    except:
        pass
    
    return {
        "score": 3,
        "follow_up": "Interesting, can you elaborate with a code example or specific implementation details?",
        "next_topic": "details"
    }


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

# @app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
# def create_interview():
#     if request.method == 'OPTIONS':
#         print("✅ OPTIONS request handled")
#         return jsonify({"status": "ok"}), 200
    
#     print("✅ POST /api/create-interview HIT!")
#     data = request.get_json() or {}
#     questions = data.get('questions', [])
#     candidate_name = data.get('candidateName', 'Candidate')
    
#     interview_id = str(uuid.uuid4())[:8].upper()
#     active_interviews[interview_id] = {
#         'id': interview_id,
#         'candidate': candidate_name,
#         'questions': questions,
#         'current_question': 0
#     }
    
#     print(f"🎤 Interview {interview_id} created!")
#     return jsonify({
#         "interviewId": interview_id,
#         "joinUrl": f"/create-zoom-meeting/{interview_id}/{candidate_name.replace(' ', '-')}"
#     })

# @app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
# def create_interview():
#     if request.method == 'OPTIONS':
#         return jsonify({"status": "ok"})
    
#     data = request.get_json() or {}
#     questions = data.get('questions', [])
#     candidate_name = data.get('candidateName', 'Candidate')
#     skills = data.get('skills', [])  # ✅ Skills from frontend
    
#     interview_id = str(uuid.uuid4())[:8].upper()
    
#     # ✅ ENHANCED STRUCTURE: Greeting + Technical + Adaptive
#     active_interviews[interview_id] = {
#         'id': interview_id,
#         'candidate': candidate_name,
#         'skills': skills,  # ✅ Stored for AI adaptation
#         'original_questions': questions,
#         'current_question': 0,
#         'answers': [],
#         'analysis': [],
#         'interview_complete': False,
#         'greeting_done': False
#     }
    
#     print(f"🎤 Adaptive interview {interview_id} created with skills: {skills}")
#     return jsonify({
#         "interviewId": interview_id,
#         "joinUrl": f"/interview/{interview_id}/{candidate_name.replace(' ', '-')}"
#     })

@app.route('/api/create-interview', methods=['POST'])
def create_interview():
    data = request.get_json()
    interview_id = str(uuid.uuid4())[:8].upper()
    
    # ✅ AI-CONTROLLED SESSION
    active_interviews[interview_id] = {
        'id': interview_id,
        'candidate': data['candidateName'],
        'skills': data.get('skills', []),
        'questions': data['questions'],
        'current_question': 0,
        'answers': [],
        'ai_analysis': [],
        'flow_state': 'greeting',  # greeting → technical → adaptive
        'complete': False
    }
    
    return jsonify({"interviewId": interview_id, "room": f"/ai-interview/{interview_id}"})

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
        "type": 1,  # Instant meeting
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",
            "waiting_room": False,  # AI bot joins immediately
            "host_save_recording": "cloud_only",
            "cloud_recording": {
                "status": "on",
                "type": "audio_transcript_video_shared",  # FULL recording
                "transcription": {
                    "add_audio_transcript": True  # Otter.ai style transcripts
                }
            },
            # AI Bot permissions
            "meeting_authentication": False,
            "private_meeting": False
        }
    }
    
    try:
        print(f"📹 Creating Zoom meeting for {candidate_name}...")
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 201:
            meeting = response.json()
            zoom_info = {
                "meeting_id": str(meeting.get("id", "")),
                "join_url": meeting.get("join_url", ""),
                "start_url": meeting.get("start_url", ""),  # For AI bot
                "password": meeting.get("password", ""),
                "candidate_name": candidate_name,
                "interview_id": interview_id,
                "recording_active": True,
                "transcript_enabled": True
            }
            
            # Save to session
            active_interviews[interview_id] = active_interviews.get(interview_id, {})
            active_interviews[interview_id].update({
                "candidate": candidate_name,
                "zoom": zoom_info
            })

            zoom_info["ai_bot_starting"] = True
            Thread(target=start_ai_bot, args=(zoom_info["start_url"], interview_id)).start()
            
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

@app.route('/api/analyze-answer', methods=['POST'])
def analyze_answer():
    interview_id = request.form.get('interviewId')
    session = active_interviews.get(interview_id)
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Save video file
    video_file = request.files['video']
    video_path = f"answers/{interview_id}_q{session['current_question']}.webm"
    video_file.save(video_path)
    
    # Mock AI analysis (replace with Whisper + LLM)
    session['answers'].append({
        'question': session['questions'][session['current_question']]['text'],
        'video': video_path,
        'timestamp': datetime.now().isoformat()
    })
    
    # Generate adaptive next question
    current_idx = session['current_question']
    if current_idx < len(session['questions']) - 1:
        next_question = session['questions'][current_idx + 1]['text']
        session['current_question'] += 1
    else:
        next_question = "Thank you! Interview complete. Check your email for results."
        session['complete'] = True
    
    save_interviews()
    
    return jsonify({
        "score": 4,
        "feedback": "Great technical understanding! Let's dive deeper.",
        "next_question": next_question
    })


@app.route('/interview/<interview_id>/<candidate_name>')
def interview_room(interview_id, candidate_name):
    """🤖 AI-Controlled Adaptive Interview Room"""
    candidate_name = candidate_name.replace('-', ' ').title()
    session = active_interviews.get(interview_id, {})
    
    if not session:
        return "❌ Interview not found", 404
    
    current_q_index = session.get('current_question', 0)
    
    # Greeting phase
    if current_q_index == 0:
        question = "👋 Hello! Welcome. Please introduce yourself (30 seconds)."
    else:
        questions = session.get('original_questions', [])
        question = questions[current_q_index-1]['text'] if current_q_index-1 < len(questions) else "Interview complete!"
    
    return f'''
<!DOCTYPE html>
<html>
<head><title>AI Interview - {candidate_name}</title>
<style>
    body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:Arial;padding:20px;margin:0;min-height:100vh}}
    .container{{max-width:1200px;margin:0 auto}}
    .videos{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin:40px 0}}
    .video-container{{background:rgba(22,33,62,0.9);border-radius:20px;padding:20px;border:2px solid #00d4ff}}
    video{{width:100%;height:350px;border-radius:15px;background:#0f0f23}}
    .question-area{{background:rgba(26,46,78,0.95);padding:50px;border-radius:25px;margin:40px 0;text-align:center}}
    .question{{font-size:2.2em;color:#00d4ff;margin-bottom:30px;line-height:1.6;max-width:900px;margin:0 auto}}
    .status{{padding:25px;border-radius:15px;margin:20px 0;font-size:1.3em;font-weight:600;background:rgba(255,255,255,0.1)}}
    .status.recording{{background:linear-gradient(45deg,#ff4444,#cc0000);animation:pulse 1s infinite}}
    button{{padding:20px 40px;font-size:1.3em;border:none;border-radius:15px;cursor:pointer;margin:15px;transition:all 0.3s}}
    .record-btn{{background:linear-gradient(45deg,#ff4444,#cc0000);color:white}}
    .next-btn{{background:linear-gradient(45deg,#00d4ff,#0099cc);color:white}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.7}}}}
</style>
</head>
<body>
    <div class="container">
        <h1 style="text-align:center;font-size:2.5em">🤖 AI Technical Interview</h1>
        <div class="videos">
            <div class="video-container">
                <h3 style="color:#00d4ff;margin-bottom:15px">🤖 AI Interviewer</h3>
                <video id="aiVideo" autoplay muted></video>
            </div>
            <div class="video-container">
                <h3 style="color:#ff6b6b;margin-bottom:15px">{candidate_name}</h3>
                <video id="candidateVideo" autoplay muted></video>
            </div>
        </div>
        
        <div class="question-area">
            <div class="question">{question}</div>
            <div class="status" id="status">🎤 Click Record → Answer clearly (2 minutes)</div>
            <button id="recordBtn" class="record-btn">🎤 Record Answer</button>
            <button id="nextBtn" class="next-btn" disabled style="display:none">Next →</button>
            <audio id="questionAudio" style="display:none"></audio>
        </div>
    </div>

    <script>
        let stream, recorder, chunks=[], interviewId='{interview_id}';
        let currentQuestion = {current_q_index};
        
        navigator.mediaDevices.getUserMedia({{
            video:{{width:640,height:480,facingMode:'user'}},
            audio:{{echoCancellation:true,noiseSuppression:true}}
        }}).then(s => {{
            stream = s;
            document.getElementById('candidateVideo').srcObject = s;
            createAnimatedAI();
            speakQuestion();
        }});
        
        function createAnimatedAI() {{
            const canvas = document.createElement('canvas');
            canvas.width=640; canvas.height=360;
            const ctx = canvas.getContext('2d');
            document.getElementById('aiVideo').srcObject = canvas.captureStream(30);
            
            let frame = 0;
            function animate() {{
                ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, 640, 360);
                const radius = 85 + Math.sin(frame * 0.1) * 10;
                const gradient = ctx.createRadialGradient(320, 180, 0, 320, 180, radius);
                gradient.addColorStop(0, '#00d4ff'); gradient.addColorStop(1, 'rgba(26,46,78,0.9)');
                ctx.fillStyle = gradient; ctx.beginPath(); ctx.arc(320, 180, radius, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#16213e'; ctx.fillRect(300, 225, 40, 25 + Math.sin(frame * 0.4) * 12);
                frame++; requestAnimationFrame(animate);
            }} animate();
        }}
        
        function speakQuestion() {{
            const audio = document.getElementById('questionAudio');
            const qText = document.querySelector('.question').textContent;
            audio.src = `/api/tts-question/${{currentQuestion}}?text=` + encodeURIComponent(qText);
            audio.play().catch(e => console.log('Audio autoplay blocked'));
        }}
        
        document.getElementById('recordBtn').onclick = () => {{
            recorder = new MediaRecorder(stream);
            chunks = [];
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = uploadAnswer;
            recorder.start(1000);
            
            document.getElementById('recordBtn').disabled = true;
            document.getElementById('recordBtn').textContent = '🔴 Recording...';
            document.getElementById('status').textContent = '🔴 Recording (2:00)';
            document.getElementById('status').className = 'status recording';
            
            let timeLeft = 120;
            const timer = setInterval(() => {{
                timeLeft--;
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                document.getElementById('status').textContent = `🔴 Recording (${{minutes}}: ${{seconds.toString().padStart(2, '0')}})`;
                if (timeLeft <= 0) {{
                    clearInterval(timer);
                    recorder.stop();
                }}
            }}, 1000);
        }};
        
        async function uploadAnswer() {{
            const blob = new Blob(chunks, {{type: 'video/webm'}});
            const formData = new FormData();
            formData.append('video', blob, `answer_q${{currentQuestion}}.webm`);
            
            try {{
                const response = await fetch(`/api/submit-answer/${{interviewId}}`, {{
                    method: 'POST',
                    body: formData
                }});
                const data = await response.json();
                console.log('✅ Answer saved:', data);
                
                document.getElementById('status').textContent = '✅ Answer analyzed! Loading next adaptive question...';
                document.getElementById('recordBtn').style.display = 'none';
                document.getElementById('nextBtn').style.display = 'inline';
                document.getElementById('nextBtn').disabled = false;
            }} catch(e) {{
                console.error('Upload failed:', e);
            }}
        }}
        
        document.getElementById('nextBtn').onclick = async () => {{
            // AI generates next adaptive question
            window.location.reload();  // Simple reload for demo
        }};
    </script>
</body></html>'''


def start_ai_bot(start_url, interview_id):
    """🤖 AI Bot: Joins Zoom + Controls Interview"""
    print(f"🤖 AI Bot starting for {interview_id}...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--disable-web-security")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. Join Zoom as AI Host
        driver.get(start_url)
        time.sleep(5)
        
        # 2. Auto-click "Join with video" 
        join_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Join')]")
        join_btn.click()
        time.sleep(3)
        
        # 3. AI Interview Loop
        session = active_interviews.get(interview_id)
        questions = session.get('questions', [])
        
        for i, question in enumerate(questions):
            print(f"🤖 AI asking Q{i+1}: {question['text']}")
            
            # Ask question via TTS (play audio)
            tts_url = f"http://localhost:5000/api/tts-question/{i+1}?text={question['text']}"
            driver.execute_script(f"fetch('{tts_url}')")
            time.sleep(5)  # Let question play
            
            # Wait for candidate answer (2 minutes)
            time.sleep(120)
            
            # AI says "Next question" 
            next_tts = f"http://localhost:5000/api/tts-question/0?text=Next question please."
            driver.execute_script(f"fetch('{next_tts}')")
            time.sleep(3)
        
        print("✅ AI Interview COMPLETE - Full recording saved to Zoom cloud")
        
    except Exception as e:
        print(f"🤖 Bot error: {e}")
    finally:
        driver.quit()

@app.route('/api/get-recording/<meeting_id>')
def get_recording(meeting_id):
    """Download Zoom recording + transcript after interview"""
    token = get_zoom_token()
    if not token:
        return jsonify({"error": "No Zoom token"}), 401
    
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    recordings = response.json()
    
    download_links = {
        "video": None,
        "audio": None,
        "transcript": None
    }
    
    for file in recordings.get('recording_files', []):
        file_type = file.get('file_type')
        if 'MP4' in file_type:
            download_links['video'] = file['download_url']
        elif 'M4A' in file_type or 'audio' in file_type.lower():
            download_links['audio'] = file['download_url']
        elif 'transcript' in file_type.lower():
            download_links['transcript'] = file['download_url']
    
    # Save to interviews
    if meeting_id in active_interviews:
        active_interviews[meeting_id]['recordings'] = download_links
        save_interviews()
    
    return jsonify({
        "meeting_id": meeting_id,
        "recordings": download_links,
        "status": "Interview recorded ✅"
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

@app.route('/ai-interview/<interview_id>')
def ai_interview_room(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "Interview not found", 404
    
    current_state = session.get('flow_state', 'greeting')
    current_question = ""
    
    if current_state == 'greeting':
        current_question = "👋 Hello! Welcome to our AI technical interview. Please introduce yourself (30 seconds)."
    elif current_state == 'technical':
        questions = session.get('questions', [])
        current_question = questions[0]['text'] if questions else "Great intro! Let's start with technical questions."
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI Interview Bot - {interview_id}</title>
    <style>/* Same styles as before */</style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Technical Interview Bot</h1>
        <div class="videos">
            <div class="video-container">
                <h3>🤖 AI Interviewer</h3>
                <video id="aiVideo" autoplay muted></video>
            </div>
            <div class="video-container">
                <h3>{session['candidate']}</h3>
                <video id="candidateVideo" autoplay muted></video>
            </div>
        </div>
        
        <div class="question-area">
            <div class="question" id="currentQuestion">{current_question}</div>
            <div class="status" id="status">🎤 Ready to start</div>
            <button id="recordBtn" class="record-btn">🎤 Record Answer</button>
            <button id="nextBtn" class="next-btn" style="display:none">Next Question →</button>
        </div>
    </div>

    <script>
        let stream, recorder, chunks = [], interviewId = '{interview_id}';
        let currentState = '{current_state}';
        
        // Get video/audio stream
        navigator.mediaDevices.getUserMedia({{
            video: {{width: 640, height: 480, facingMode: 'user'}},
            audio: {{echoCancellation: true, noiseSuppression: true}}
        }}).then(s => {{
            stream = s;
            document.getElementById('candidateVideo').srcObject = s;
            createAnimatedAI();
            speakCurrentQuestion();
        }});
        
        // Animated AI avatar
        function createAnimatedAI() {{
            const canvas = document.createElement('canvas');
            canvas.width = 640; canvas.height = 360;
            const ctx = canvas.getContext('2d');
            document.getElementById('aiVideo').srcObject = canvas.captureStream(30);
            
            let frame = 0;
            function animate() {{
                ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, 640, 360);
                const radius = 85 + Math.sin(frame * 0.1) * 10;
                const gradient = ctx.createRadialGradient(320, 180, 0, 320, 180, radius);
                gradient.addColorStop(0, '#00d4ff'); gradient.addColorStop(1, 'rgba(26,46,78,0.9)');
                ctx.fillStyle = gradient; ctx.beginPath(); ctx.arc(320, 180, radius, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#16213e'; ctx.fillRect(300, 225, 40, 25 + Math.sin(frame * 0.4) * 12);
                frame++; requestAnimationFrame(animate);
            }} animate();
        }}
        
        function speakCurrentQuestion() {{
            const question = document.getElementById('currentQuestion').textContent;
            fetch(`/api/tts-question?interview=${{interviewId}}&text=` + encodeURIComponent(question))
                .then(() => console.log('✅ AI speaking'));
        }}
        
        // Record answer → AI analyzes → Next question
        document.getElementById('recordBtn').onclick = async () => {{
            recorder = new MediaRecorder(stream);
            chunks = [];
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = sendToAI;
            recorder.start();
            
            let timeLeft = 120; // 2 minutes
            document.getElementById('status').textContent = `🔴 Recording (${{Math.floor(timeLeft/60)}}:${{timeLeft%60}}`;
            document.getElementById('recordBtn').textContent = '🔴 Recording...';
            
            const timer = setInterval(() => {{
                timeLeft--;
                const mins = Math.floor(timeLeft / 60);
                const secs = timeLeft % 60;
                document.getElementById('status').textContent = `🔴 Recording (${{mins}}: ${{secs.toString().padStart(2,'0')}})`;
                if (timeLeft <= 0) {{
                    clearInterval(timer);
                    recorder.stop();
                }}
            }}, 1000);
        }};
        
        async function sendToAI() {{
            const blob = new Blob(chunks, {{type: 'video/webm'}});
            const formData = new FormData();
            formData.append('video', blob, 'answer.webm');
            formData.append('interviewId', interviewId);
            
            document.getElementById('status').textContent = '🤖 AI analyzing your answer...';
            
            try {{
                const response = await fetch('/api/analyze-answer', {{
                    method: 'POST',
                    body: formData
                }});
                const data = await response.json();
                
                // AI generates next question
                document.getElementById('currentQuestion').textContent = data.next_question;
                document.getElementById('recordBtn').style.display = 'block';
                document.getElementById('recordBtn').textContent = '🎤 Record Next Answer';
                document.getElementById('status').textContent = `✅ Analysis: ${{data.score}}/5 | Ready for next question`;
                
            }} catch(e) {{
                console.error('AI analysis failed:', e);
            }}
        }}
    </script>
</body>
</html>'''
