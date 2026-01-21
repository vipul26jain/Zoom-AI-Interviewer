from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import json
import re
import requests
import base64
import time
import tempfile

load_dotenv()
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500", "https://zoom-ai-interviewer-production.up.railway.app/", "https://zoom-ai-interviewer-production.up.railway.app/"])

# 🔥 ULTIMATE CORS CONFIGURATION (UNCHANGED)
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# ✅ WORKING MODELS (UNCHANGED)
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

# 🔥 NEW: Add answers array to interview sessions
def ensure_interview_structure(interview_id):
    session = active_interviews.get(interview_id)
    if session and 'answers' not in session:
        session['answers'] = []
        session['full_session_blob'] = None
        session['evaluation'] = None
    return session

# ALL YOUR ORIGINAL FUNCTIONS (UNCHANGED)
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
            
            if (hasattr(response, 'choices') and 
                isinstance(response.choices, list) and 
                len(response.choices) > 0 and 
                hasattr(response.choices[0], 'message') and 
                hasattr(response.choices[0].message, 'content')):
                
                content = response.choices[0].message.content.strip()
                print(f"✅ SUCCESS with {model}: {content[:60]}...")
                
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

# Safe imports with fallbacks (UNCHANGED)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

# ALL YOUR ORIGINAL ROUTES (UNCHANGED until interview room)
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
    
    prompt = f"""Job: {job_description}
Resume: {resume_text or 'None'}

Generate 6 targeted interview questions. Return ONLY JSON."""
    
    questions = safe_groq_call(prompt)
    print(f"AI questions : {questions}")
    if questions: 
        print(f"✅ Generated {len(questions)} AI questions")
        return jsonify({"questions": questions})
    
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

INTERVIEWS_FILE = "interviews.json"

def load_interviews():
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
            print(f"✅ Loaded {len(active_interviews)} interviews")
        except:
            print("⚠️ Corrupted interviews file, starting fresh")

def save_interviews():
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save failed: {e}")

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
        'current_question': 0,
        'answers': [],  # 🔥 NEW: Added for continuous recording
        'full_session': None,
        'evaluation': None,
        'status': 'active'
    }
    
    save_interviews()
    print(f"🎤 Interview {interview_id} created!")
    return jsonify({
        "interviewId": interview_id,
        "joinUrl": f"/interview/{interview_id}"
    })

# 🔥 NEW: Continuous recording endpoints
@app.route('/api/start-continuous-recording/<interview_id>', methods=['POST'])
def start_continuous_recording(interview_id):
    session = ensure_interview_structure(interview_id)
    if session:
        session['recording_active'] = True
        session['recording_start_time'] = time.time()
        save_interviews()
        return jsonify({"status": "continuous_recording_started"})
    return jsonify({"error": "Interview not found"}), 404

@app.route('/api/finish-interview/<interview_id>', methods=['POST'])
def finish_interview(interview_id):
    session = ensure_interview_structure(interview_id)
    if not session:
        return jsonify({"error": "Interview not found"}), 404
    
    full_video = request.files.get('full_session')
    if full_video:
        os.makedirs("recordings", exist_ok=True)
        filename = f"full_session_{interview_id}.webm"
        filepath = f"recordings/{filename}"
        full_video.save(filepath)
        session['full_session'] = filepath
        
        # 🔥 AI EVALUATION
        if client and os.path.exists(filepath):
            try:
                with open(filepath, "rb") as audio_file:
                    # Transcribe with Whisper (Groq supports it)
                    transcription = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=audio_file
                    )
                
                full_transcript = transcription.text
                eval_prompt = f"""
                Interview Questions: {json.dumps(session['questions'])}
                Full Transcript: {full_transcript}
                
                Evaluate candidate (JSON only):
                {{"score": 8, "feedback": "detailed feedback", "recommendation": "hire"}}
                """
                
                response = client.chat.completions.create(
                    model=WORKING_MODELS[0],
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0.1
                )
                
                session['evaluation'] = json.loads(response.choices[0].message.content)
            except Exception as e:
                print(f"Evaluation failed: {e}")
                session['evaluation'] = {"score": "N/A", "feedback": "Transcription failed"}
        
        session['status'] = 'completed'
        save_interviews()
    
    return jsonify({
        "status": "completed",
        "evaluation": session.get('evaluation', {})
    })

@app.route('/api/results/<interview_id>')
def show_results(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "Interview not found", 404
    
    eval_data = session.get('evaluation', {})
    return f'''
    <!DOCTYPE html>
    <html><head><title>Results - {session['candidate']}</title>
    <style>body{{font-family:Arial;background:#1a1a2e;color:white;padding:40px}} .score{{font-size:3em;color:#00d4ff}}</style>
    </head>
    <body>
        <h1>📊 Interview Results</h1>
        <div class="score">Score: {eval_data.get("score", "N/A")}/10</div>
        <h3>{session['candidate']}</h3>
        <div style="background:rgba(255,255,255,0.1);padding:20px;border-radius:10px">
            <strong>Feedback:</strong> {eval_data.get("feedback", "No evaluation")}
        </div>
        <pre style="background:#16213e;padding:20px;border-radius:10px">{json.dumps(session, indent=2)}</pre>
    </body></html>
    '''

# 🔥 MODIFIED: YOUR ORIGINAL INTERVIEW ROOM with CONTINUOUS RECORDING
@app.route('/interview/<interview_id>')
def ai_interview_room(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text'] if current_q < len(session['questions']) else "🎉 Interview Complete!"
    is_complete = current_q >= len(session['questions'])
    is_first_question = current_q == 0
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI Interview - {session['candidate']}</title>
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:Arial,sans-serif;min-height:100vh;padding:20px}}.container{{max-width:1200px;margin:0 auto}}.videos{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}}.video-container{{background:rgba(15,15,35,0.8);border-radius:15px;padding:15px;border:2px solid #00d4ff}}.question-area{{background:rgba(22,33,62,0.95);padding:30px;border-radius:20px;margin:20px 0;text-align:center;border:2px solid #00d4ff}}.status{{padding:15px;border-radius:10px;margin:15px 0;font-weight:600}}.recording{{background:#ff4444;color:white}}.button{{padding:15px 30px;font-size:1.1em;border:none;border-radius:10px;cursor:pointer;margin:10px}}.record-btn{{background:#ff4444;color:white}}.next-btn{{background:#00d4ff;color:white}}.finish-btn{{background:#ff6b6b;color:white}}.q-counter{{position:absolute;top:20px;right:20px;background:rgba(0,212,255,0.2);padding:10px;border-radius:10px}}</style>
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
            <div class="status recording" id="status">
                {'' if is_complete else '🔴 CONTINUOUS RECORDING ACTIVE - Full session captured automatically!'}
            </div>
            <div>
                {'''<button id="startInterviewBtn" class="button record-btn">🚀 START FULL INTERVIEW RECORDING</button>''' if is_first_question else ''}
                <button id="askBtn" class="button record-btn" style="display:{'block' if not is_first_question else 'none'}" disabled>🎤 AI Ask Question</button>
                <button id="recordBtn" class="button record-btn" style="display:none">🔴 Record Answer (60s)</button>
                <button id="nextBtn" class="button next-btn" disabled>Next →</button>
                {'''<button id="finishBtn" class="finish-btn button" style="display:block">✅ FINISH & EVALUATE</button>''' if is_complete else ''}
            </div>
        </div>
    </div>
    
    <script>
        const interviewId = "{interview_id}";
        const currentQuestionIndex = {current_q};
        let mediaStream = null;
        let recorder = null;
        let chunks = [];
        let continuousRecording = false;
        
        // YOUR ORIGINAL CAMERA INIT (UNCHANGED)
        window.addEventListener('load', async function() {{
            const statusEl = document.getElementById("status");
            const videoEl = document.getElementById("candidateVideo");
            
            try {{
                statusEl.textContent = "🎥 Requesting camera access...";
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{width: {{ideal: 640}}, height: {{ideal: 480}}, facingMode: "user"}},
                    audio: {{echoCancellation: true, noiseSuppression: true}}
                }});
                
                mediaStream = stream;
                videoEl.srcObject = stream;
                videoEl.play();
                
                statusEl.textContent = {"First Question - Click START FULL INTERVIEW" if {current_q} == 0 else "Ready! Click AI Ask Question"};
                document.getElementById("askBtn").disabled = false;
                if (document.getElementById("startInterviewBtn")) {{
                    document.getElementById("startInterviewBtn").disabled = false;
                }}
                createAnimatedAI();
                
            }} catch (error) {{
                console.error("❌ FULL ERROR:", error);
                statusEl.innerHTML = `❌ Camera failed: <strong>${{error.name}}</strong><br>${{error.message}}`;
            }}
        }});
        
        // YOUR ORIGINAL AI ANIMATION (UNCHANGED)
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
        
        // 🔥 NEW: START CONTINUOUS RECORDING (First question only)
        document.getElementById("startInterviewBtn")?.onclick = async function() {{
            await fetch(`/api/start-continuous-recording/${{interviewId}}`, {{method: 'POST'}});
            
            // Start continuous recording
            recorder = new MediaRecorder(mediaStream);
            chunks = [];
            recorder.ondataavailable = function(e) {{ chunks.push(e.data); }};
            recorder.start(250);  // Collect chunks continuously
            
            document.getElementById("status").innerHTML = "🔴 FULL INTERVIEW RECORDING STARTED<br>AI will guide through all questions";
            document.getElementById("startInterviewBtn").style.display = "none";
            continuousRecording = true;
        }};
        
        // YOUR ORIGINAL AI ASK QUESTION (MODIFIED for continuous recording)
        document.getElementById("askBtn")?.onclick = function() {{
            const utterance = new SpeechSynthesisUtterance("{question}");
            utterance.rate = 0.9; utterance.pitch = 1.1;
            speechSynthesis.speak(utterance);
            
            document.getElementById("status").textContent = "🎤 Question asked! Answer freely (continuous recording active)";
            document.getElementById("recordBtn").style.display = "none";  // Hide per-question recording
            document.getElementById("askBtn").style.display = "none";
            document.getElementById("nextBtn").disabled = false;
        }};
        
        // YOUR ORIGINAL NEXT BUTTON (MODIFIED)
        document.getElementById("nextBtn")?.onclick = function() {{ 
            fetch(`/api/next-question/${{interviewId}}`, {{method: 'POST'}}).then(() => window.location.reload()); 
        }};
        
        // 🔥 NEW: FINISH INTERVIEW (Last question only)
        document.getElementById("finishBtn")?.onclick = async function() {{
            if (recorder && continuousRecording) {{
                recorder.stop();
                recorder.onstop = async function() {{
                    const blob = new Blob(chunks, {{type: "video/webm"}});
                    const formData = new FormData();
                    formData.append("full_session", blob, `full_session_${{interviewId}}.webm`);
                    
                    const response = await fetch(`/api/finish-interview/${{interviewId}}`, {{
                        method: "POST",
                        body: formData
                    }});
                    const result = await response.json();
                    
                    alert(`✅ Interview Complete!\nScore: ${{result.evaluation.score || 'Pending'}}/10`);
                    window.location.href = `/api/results/${{interviewId}}`;
                }};
            }}
        }};
    </script>
</body>
</html>'''

# YOUR ORIGINAL ROUTES (UNCHANGED)
@app.route('/api/next-question/<interview_id>', methods=['POST'])
def next_question(interview_id):
    session = active_interviews.get(interview_id)
    if session:
        session['current_question'] += 1
        save_interviews()
        print(f"➡️ {interview_id}: Q{session['current_question']}")
    return jsonify({"status": "next"})

@app.route('/api/submit-answer/<interview_id>', methods=['POST', 'OPTIONS'])
def submit_answer(interview_id):
    print("Enter Submit Answer")
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    session = ensure_interview_structure(interview_id)
    if session:
        video_file = request.files.get('video')
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
            save_interviews()
            print(f"✅ Saved VIDEO: {filename}")
    
    return jsonify({"status": "saved"})

# ALL YOUR ZOOM + OTHER ROUTES (UNCHANGED - keeping exact original)
def create_zoom_meeting(interview_id, candidate_name):
    if not ZOOM_API_KEY or not ZOOM_API_SECRET:
        return {"meetingId": "fake-123-456-789", "joinUrl": f"/zoom-fake/{interview_id}"}
    
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {get_zoom_token()}",
        "Content-Type": "application/json"
    }
    data = {
        "topic": f"AI Interview - {candidate_name}",
        "type": 2,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",
            "meeting_recording": {"recording_type": "audio_only"}
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

def get_zoom_token():
    import jwt
    import calendar
    payload = {
        'iss': ZOOM_API_KEY,
        'exp': calendar.timegm(time.gmtime()) + 3600
    }
    return jwt.encode(payload, ZOOM_API_SECRET, algorithm='HS256')

@app.route('/api/create-zoom-interview/<interview_id>', methods=['POST'])
def create_zoom_interview(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return jsonify({"error": "Interview not found"}), 404
    
    zoom_info = create_zoom_meeting(interview_id, session['candidate'])
    
    return jsonify({
        "zoomMeetingId": zoom_info["meetingId"],
        "joinUrl": zoom_info["joinUrl"],
        "interviewId": interview_id
    })

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

@app.route('/debug')
def debug():
    return jsonify({
        "active_interviews": list(active_interviews.keys()),
        "count": len(active_interviews)
    })

if __name__ == '__main__':
    print("🚀 Backend running on http://localhost:5000")
    app.run(port=5000, debug=True)
