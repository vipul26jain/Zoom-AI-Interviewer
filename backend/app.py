from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import json
import re
import requests

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
        "joinUrl": f"/interview/{interview_id}"
    })

# @app.route('/interview/<interview_id>')
# def interview_room(interview_id):
#     print("Enter Interview Room1")
#     session = active_interviews.get(interview_id)
#     print("Session1:", session)
#     return f"Interview room for {session['candidate'] if session else 'NOT FOUND'}"


@app.route('/interview/<interview_id>')
def ai_interview_room(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text'] if current_q < len(session['questions']) else "🎉 Interview Complete!"
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI Interview - {session['candidate']}</title>
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:Arial,sans-serif;min-height:100vh;padding:20px}}.container{{max-width:1200px;margin:0 auto}}.videos{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}}.video-container{{background:rgba(15,15,35,0.8);border-radius:15px;padding:15px;border:2px solid #00d4ff}}.question-area{{background:rgba(22,33,62,0.95);padding:30px;border-radius:20px;margin:20px 0;text-align:center;border:2px solid #00d4ff}}.status{{padding:15px;border-radius:10px;margin:15px 0;font-weight:600}}.recording{{background:#ff4444;color:white}}.button{{padding:15px 30px;font-size:1.1em;border:none;border-radius:10px;cursor:pointer;margin:10px}}.record-btn{{background:#ff4444;color:white}}.next-btn{{background:#00d4ff;color:white}}.q-counter{{position:absolute;top:20px;right:20px;background:rgba(0,212,255,0.2);padding:10px;border-radius:10px}}</style>
</head>
<body>
    <div class="container">
        <div class="q-counter">Q{current_q + 1}/{len(session['questions'])}</div>
        <h1 style="text-align:center;font-size:2.5em;margin-bottom:20px">🤖 AI Interview - {session['candidate']}</h1>
        
        <div class="videos">
            <div class="video-container">
                <h3 style="color:#00d4ff;margin-bottom:10px">🤖 AI Interviewer</h3>
                <video id="aiVideo" width="100%" height="300" style="border-radius:10px;background:#0f0f23" autoplay muted></video>
            </div>
            <div class="video-container">
                <h3 style="color:#ff6b6b;margin-bottom:10px">👤 You</h3>
                <video id="candidateVideo" width="100%" height="300" autoplay muted playsinline style="border-radius:10px;background:#0f0f23"></video>
            </div>
        </div>
        
        <div class="question-area">
            <div style="font-size:1.8em;color:#00d4ff;margin-bottom:20px">{question}</div>
            <div class="status" id="status">🔄 Initializing camera...</div>
            <div>
                <button id="askBtn" class="button record-btn" disabled>🎤 AI Ask Question</button>
                <button id="recordBtn" class="button record-btn" disabled>🔴 Record Answer (60s)</button>
                <button id="nextBtn" class="button next-btn" disabled>Next →</button>
            </div>
        </div>
    </div>
    
    <script>
        // ✅ GLOBAL VARIABLES - Accessible EVERYWHERE
        const interviewId = "{interview_id}";
        const currentQuestionIndex = {current_q};
        let mediaStream = null;
        let recorder = null;
        let chunks = [];
        
        // 1. Initialize Camera
        navigator.mediaDevices.getUserMedia({{
            video: {{width: 640, height: 480, facingMode: "user"}},
            audio: true
        }}).then(function(stream) {{
            mediaStream = stream;
            document.getElementById("candidateVideo").srcObject = stream;
            createAnimatedAI();
            document.getElementById("status").textContent = "✅ Ready! Click AI Ask Question";
            document.getElementById("askBtn").disabled = false;
        }}).catch(function(e) {{
            document.getElementById("status").innerHTML = "❌ Camera/mic required";
        }});
        
        // 2. AI Animation
        function createAnimatedAI() {{
            const video = document.getElementById("aiVideo");
            const canvas = document.createElement("canvas");
            canvas.width = 640; canvas.height = 360;
            const ctx = canvas.getContext("2d");
            video.srcObject = canvas.captureStream(30);
            
            let frame = 0;
            function animate() {{
                ctx.fillStyle = "#1a1a2e"; ctx.fillRect(0, 0, 640, 360);
                const radius = 80 + Math.sin(frame * 0.1) * 8;
                const gradient = ctx.createRadialGradient(320, 180, 0, 320, 180, radius);
                gradient.addColorStop(0, "#00d4ff"); gradient.addColorStop(1, "rgba(0,212,255,0.3)");
                ctx.fillStyle = gradient; ctx.beginPath(); ctx.arc(320, 180, radius, 0, Math.PI*2); ctx.fill();
                ctx.fillStyle = "#16213e"; ctx.fillRect(300, 220, 40, 20 + Math.sin(frame * 0.3) * 10);
                frame++; requestAnimationFrame(animate);
            }}
            animate();
        }}
        
        // 3. AI Ask Question (TTS)
        document.getElementById("askBtn").onclick = function() {{
            const utterance = new SpeechSynthesisUtterance("{question}");
            utterance.rate = 0.9; utterance.pitch = 1.1;
            speechSynthesis.speak(utterance);
            
            document.getElementById("status").textContent = "🎤 Question asked! Ready to record.";
            document.getElementById("recordBtn").disabled = false;
            document.getElementById("askBtn").style.display = "none";
        }};
        
        // 4. Record Answer
        document.getElementById("recordBtn").onclick = function() {{
            if (!mediaStream) return alert("No camera");
            
            recorder = new MediaRecorder(mediaStream);
            chunks = [];
            recorder.ondataavailable = function(e) {{ chunks.push(e.data); }};
            recorder.onstop = uploadAnswer;  // ✅ Calls GLOBAL uploadAnswer()
            
            recorder.start(250);
            
            let timeLeft = 60;
            const status = document.getElementById("status");
            status.textContent = "🔴 Recording (1:00)";
            status.className = "recording";
            
            const timer = setInterval(function() {{
                timeLeft--;
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                status.textContent = "🔴 Recording (" + minutes + ":" + seconds.toString().padStart(2,"0") + ")";
                
                if (timeLeft <= 0) {{
                    clearInterval(timer);
                    recorder.stop();
                }}
            }}, 1000);
        }};
        
        // 5. ✅ FIXED UPLOAD - Uses GLOBAL VARIABLES
        function uploadAnswer() {{
            const questionNum = currentQuestionIndex + 1;  // ✅ GLOBAL currentQuestionIndex
            const filename = "answer_q" + questionNum + "_" + interviewId + ".webm";  // ✅ String concat
            const blob = new Blob(chunks, {{type: "video/webm"}});
            const formData = new FormData();
            formData.append("video", blob, filename);
            
            fetch("/api/submit-answer/" + interviewId, {{
                method: "POST",
                body: formData
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
                document.getElementById("status").textContent = "✅ Answer saved! Next question ready.";
                document.getElementById("status").className = "status";
                document.getElementById("recordBtn").style.display = "none";
                document.getElementById("nextBtn").disabled = false;
            }});
        }}
        
        // 6. Next Question
        document.getElementById("nextBtn").onclick = function() {{ 
            window.location.reload(); 
        }};

        // Put this at BOTTOM of your <script> section
        window.addEventListener('load', async function() {{
            const statusEl = document.getElementById("status");
            const videoEl = document.getElementById("candidateVideo");
            
            try {{
                // ✅ Show permission request
                statusEl.textContent = "🎥 Requesting camera access...";
                
                // ✅ Better constraints
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{
                        width: {{ ideal: 640 }},
                        height: {{ ideal: 480 }},
                        facingMode: {{ ideal: "user" }}  // Front camera
                    }},
                    audio: {{
                        echoCancellation: true,
                        noiseSuppression: true
                    }}
                }});
                
                // ✅ Assign stream
                mediaStream = stream;
                videoEl.srcObject = stream;
                videoEl.play();  // ✅ Force play
                
                statusEl.textContent = "✅ Camera ready! 🎤 Click AI Ask Question";
                document.getElementById("askBtn").disabled = false;
                createAnimatedAI();
                
            }} catch (error) {{
                console.error("❌ FULL ERROR:", error);
                statusEl.innerHTML = `❌ Camera failed: <strong>${{error.name}}</strong><br>${{error.message}}`;
            }}
        }});
    </script>
</body>
</html>'''



def create_zoom_meeting(interview_id, candidate_name):
    """Create Zoom meeting for interview"""
    if not ZOOM_API_KEY or not ZOOM_API_SECRET:
        return {"meetingId": "fake-123-456-789", "joinUrl": f"/zoom-fake/{interview_id}"}
    
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {get_zoom_token()}",
        "Content-Type": "application/json"
    }
    data = {
        "topic": f"AI Interview - {candidate_name}",
        "type": 2,  # Scheduled
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",
            "meeting_recording": {"recording_type": "audio_only"}
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    meeting = response.json()
    
    # Store meeting info
    active_interviews[interview_id]["zoom"] = {
        "meetingId": meeting["id"],
        "joinUrl": meeting["join_url"],
        "password": meeting.get("password", "")
    }
    save_interviews()
    
    return active_interviews[interview_id]["zoom"]

def get_zoom_token():
    """Generate Zoom JWT token"""
    import jwt
    import calendar
    payload = {
        'iss': ZOOM_API_KEY,
        'exp': calendar.timegm(time.gmtime()) + 3600
    }
    return jwt.encode(payload, ZOOM_API_SECRET, algorithm='HS256')

@app.route('/api/create-zoom-interview/<interview_id>', methods=['POST'])
def create_zoom_interview(interview_id):
    """Create Zoom meeting for existing interview"""
    session = active_interviews.get(interview_id)
    if not session:
        return jsonify({"error": "Interview not found"}), 404
    
    zoom_info = create_zoom_meeting(interview_id, session['candidate'])
    
    return jsonify({
        "zoomMeetingId": zoom_info["meetingId"],
        "joinUrl": zoom_info["joinUrl"],
        "interviewId": interview_id
    })

@app.route('/interview/<interview_id>')
def ai_zoom_interview(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text']
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Zoom AI Interview - {session['candidate']}</title>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/react.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/react-dom.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/redux.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/redux-thunk.min.js"></script>
    <script src="https://source.zoom.us/zoom-meeting-2.18.2.min.js"></script>
    <style>
        body{{margin:0;background:#1a1a2e;color:white;font-family:Arial,sans-serif;overflow:hidden}}
        #meetingSDKElement{{flex:1;height:100vh}}
        .sidebar{{position:fixed;right:20px;top:20px;width:350px;background:rgba(26,26,46,0.95);padding:20px;border-radius:15px;border:2px solid #00d4ff;max-height:80vh;overflow-y:auto}}
        .question{{font-size:1.4em;color:#00d4ff;margin-bottom:20px;padding:15px;background:rgba(0,212,255,0.1);border-radius:10px}}
        .controls{{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}}
        button{{padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-weight:600;flex:1;min-width:120px}}
        .ask-btn{{background:#00d4ff;color:white}}
        .next-btn{{background:#ff6b6b;color:white}}
        .next-btn:disabled{{opacity:0.5;background:#666}}
        .status{{padding:10px;border-radius:8px;margin:10px 0;font-weight:500}}
        .recording{{background:#ff4444 !important;color:white !important}}
        .q-counter{{position:fixed;top:20px;left:20px;background:rgba(0,212,255,0.2);padding:10px;border-radius:10px;font-weight:bold}}
    </style>
</head>
<body>
    <div class="q-counter">Q{current_q + 1}/{len(session['questions'])}</div>
    
    <!-- Zoom Meeting Container -->
    <div id="meetingSDKElement"></div>
    
    <!-- AI Agent Sidebar -->
    <div class="sidebar">
        <h2 style="color:#00d4ff;margin-bottom:15px">🤖 AI Interview Agent</h2>
        <div class="question">{question}</div>
        <div class="status" id="status">🔄 Ready to start Zoom meeting</div>
        <div class="controls">
            <button id="joinZoom" class="ask-btn">🎥 Join Zoom Meeting</button>
            <button id="askQuestion" class="ask-btn" disabled>🎤 AI Ask Question</button>
            <button id="nextQuestion" class="next-btn" disabled>Next Question →</button>
        </div>
        <div id="recordingStatus" style="margin-top:15px;display:none">
            <div class="status recording">🔴 Recording Answer...</div>
        </div>
    </div>
    
    <script>
        const interviewId = "{interview_id}";
        let client;
        let meeting;
        
        // ✅ 1. Initialize Zoom SDK
        document.getElementById("joinZoom").onclick = function() {{
            const status = document.getElementById("status");
            status.textContent = "🔄 Creating Zoom meeting...";
            
            fetch("/api/create-zoom-interview/" + interviewId, {{method:"POST"}})
            .then(r => r.json())
            .then(function(zoomData) {{
                status.textContent = "🎥 Starting Zoom meeting...";
                
                // Zoom SDK Config
                client = ZoomMtgEmbedded.createClient();
                let meetingConfig = {{
                    apiKey: "YOUR_ZOOM_SDK_KEY",  // Get from Zoom Marketplace
                    apiSecret: "YOUR_ZOOM_SDK_SECRET",
                    meetingNumber: parseInt(zoomData.zoomMeetingId),
                    password: "",
                    role: 0,
                    userName: "{session['candidate']}",
                    userEmail: "",
                    lang: "en-US",
                    signature: "",  // Generate server-side
                    china: false
                }};
                
                client.init({{
                    zoomAppRoot: document.getElementById("meetingSDKElement"),
                    language: "en-US",
                    customize: {{
                        videoHeader: "AI Interview"
                    }}
                }}).then(() => {{
                    client.join(meetingConfig).then(() => {{
                        status.textContent = "✅ In Zoom! AI will ask question now.";
                        status.className = "status";
                        document.getElementById("askQuestion").disabled = false;
                        document.getElementById("joinZoom").style.display = "none";
                    }});
                }});
            }});
        }};
        
        // ✅ 2. AI Agent Asks Question (TTS + Zoom Audio)
        document.getElementById("askQuestion").onclick = function() {{
            const status = document.getElementById("status");
            status.textContent = "🤖 AI asking question...";
            status.className = "status recording";
            
            // TTS in Zoom (plays through meeting audio)
            const utterance = new SpeechSynthesisUtterance(document.querySelector(".question").textContent);
            utterance.rate = 0.9; utterance.pitch = 1.0;
            speechSynthesis.speak(utterance);
            
            // Auto-start Zoom cloud recording
            setTimeout(() => {{
                document.getElementById("recordingStatus").style.display = "block";
                status.textContent = "🎤 Recording your answer (60 seconds)";
            }}, 3000);
            
            // Auto-next after 60 seconds
            setTimeout(() => {{
                document.getElementById("nextQuestion").disabled = false;
                status.textContent = "✅ Answer recorded! Ready for next.";
            }}, 65000);
        }};
        
        // ✅ 3. Next Question
        document.getElementById("nextQuestion").onclick = function() {{
            fetch("/api/next-question/" + interviewId, {{method:"POST"}})
            .then(() => window.location.reload());
        }};
    </script>
</body>
</html>'''

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

def create_zoom_meeting(interview_id, candidate_name):
    """✅ Uses Client ID/Secret (NOT API Key)"""
    token = get_zoom_access_token()
    
    url = f"https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "topic": f"AI Interview - {candidate_name} [{interview_id}]",
        "type": 1,  # Instant meeting
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "local"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    meeting = response.json()
    
    active_interviews[interview_id]["zoom"] = {
        "meetingId": meeting["id"],
        "joinUrl": meeting["join_url"],
        "password": meeting.get("password", "")
    }
    save_interviews()
    
    return active_interviews[interview_id]["zoom"]


@app.route('/api/submit-answer/<interview_id>', methods=['POST', 'OPTIONS'])
def submit_answer(interview_id):
    print("Enter Submit Answer")
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    session = active_interviews.get(interview_id)
    print(f"Session : {session}")
    if session:
        video_file = request.files.get('video')  # ✅ Changed from 'audio' to 'video'
        print(f"Video File : {video_file}")
        if video_file:
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
