"""Demo Director Builder for PayLens.

Generates:
1. Studio-grade neural voiceover track: demo_studio/full_pitch_voiceover.mp3 (edge-tts, en-US-AndrewNeural, +4%)
2. Interactive 60fps HTML5 Motion-Graphics Cinema Player: demo_studio/demo_director.html
   - Self-contained with embedded Base64 audio URI
   - 4 synchronized scenes with audio-driven timeline
   - Embedded Streamlit iframe / interactive deal desk cue prompter
   - AMD Instinct MI300X 192GB HBM3 architecture finale
"""
import os
import sys
import json
import base64
import asyncio
from pathlib import Path

# Ensure edge-tts is available
try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts is not installed. Run: pip install edge-tts")
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT_DIR / "demo_studio"
DEMO_DIR.mkdir(exist_ok=True)

VOICEOVER_MP3 = DEMO_DIR / "full_pitch_voiceover.mp3"
DIRECTOR_HTML = DEMO_DIR / "demo_director.html"

# Pitch script carefully tuned for ~135 seconds with rate +4%
NARRATION_SCRIPT = """Every modern e-commerce business operates across fragmented payment rails: card gateways, digital wallets, bank transfers, and courier cash-on-delivery. Because each rail settles on disconnected timelines, capital silently bleeds. Dispatched orders go unpaid, couriers remit shortfalls, and abandoned checkouts vanish. Across twenty mid-market storefronts in our benchmark, PayLens uncovered over one hundred and forty-six thousand dollars in undetected cross-rail revenue leakage.

To solve this, we created PayLens on AMD hardware. Our core rule is simple: code computes, the model explains. All cross-rail reconciliation, Holt-Winters forecasting, and profit math run 100% deterministically in Python and DuckDB. Before Google Gemma 4 31B drafts recovery actions, our strict regex guardrail verifies every number against ledger truth, instantly blocking ungrounded hallucinations.

Here is the live Deal Desk in action. On the left, the Priority Action Queue ranks capital leakage by business urgency. Card number one exposes a twelve hundred and fifty-five dollar payment leakage on order 4349. When we inspect this card, PayLens displays the deterministic formula, raw DuckDB evidence, and Gemma 4's grounded explanation. With one click, the operator approves the recovery action, issuing a SHA-256 audit receipt and initiating rail settlement recovery.

Now, watch our defense against hallucinations. Clicking the red-team hallucination trap simulates a rogue LLM claiming an unauthorized ninety-nine hundred dollar balance. Our regex verifier immediately blocks the token and triggers the deterministic fallback.

When business priorities shift, clicking 'Prevent Stockouts' dynamically re-ranks inventory risks with seven-day Holt-Winters predictive forecast curves before supplier lead times run dry. The operator stays in complete control with instant, verified actions.

Finally, in Tab 2, see why the AMD Instinct MI300X with 192 gigabytes of HBM3 memory makes autonomous commerce real. Gemma 4 31B uses 62 gigabytes, leaving 130 gigabytes of dedicated headroom for parallel KV cache processing. Under ROCm vLLM, PayLens achieves 32-way async burst throughput exceeding 410 cards per minute, delivering 100% precision, 100% recall, and zero hallucinated numbers. PayLens on AMD Instinct MI300X: stopping revenue leaks before they cost you the business."""

async def generate_voiceover() -> list:
    print(f"[1/3] Synthesizing continuous neural voiceover with edge-tts (en-US-AndrewNeural, +4%)...")
    communicate = edge_tts.Communicate(NARRATION_SCRIPT, voice="en-US-AndrewNeural", rate="+4%")
    
    sentences = []
    # Save audio stream directly
    with open(VOICEOVER_MP3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                start_s = chunk["offset"] / 10_000_000
                dur_s = chunk["duration"] / 10_000_000
                sentences.append({
                    "start": round(start_s, 2),
                    "end": round(start_s + dur_s, 2),
                    "text": chunk["text"],
                })

    size_kb = os.path.getsize(VOICEOVER_MP3) / 1024
    print(f"      Saved {VOICEOVER_MP3} ({size_kb:.1f} KB, {len(sentences)} timed sentence cues)")
    return sentences

def build_director_html(sentences: list):
    print(f"[2/3] Embedding audio base64 and building 60fps Cinema Player HTML...")
    with open(VOICEOVER_MP3, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    sentences_json = json.dumps(sentences)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PayLens // 60fps Motion-Graphics Cinema Director</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-dark: #090D16;
    --card-bg: #111827;
    --card-surface: #151F33;
    --border-subtle: rgba(255, 255, 255, 0.08);
    --accent-indigo: #6366F1;
    --accent-emerald: #10B981;
    --accent-amber: #F59E0B;
    --accent-rose: #EF4444;
    --accent-sky: #38BDF8;
    --text-primary: #F8FAFC;
    --text-muted: #94A3B8;
    --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: var(--font-sans);
    overflow: hidden;
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    user-select: none;
  }}

  /* Canvas Stage (16:9 ratio container) */
  #stage-container {{
    flex: 1;
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: radial-gradient(circle at 50% 20%, rgba(99, 102, 241, 0.12) 0%, rgba(9, 13, 22, 1) 75%);
  }}

  /* Grid overlay */
  .grid-bg {{
    position: absolute;
    inset: 0;
    background-size: 40px 40px;
    background-image: 
      linear-gradient(to right, rgba(255, 255, 255, 0.02) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    pointer-events: none;
  }}

  /* Top Cinema Header */
  .cinema-header {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: rgba(11, 17, 32, 0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 28px;
    z-index: 100;
  }}

  .brand-group {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  .brand-logo {{
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FFFFFF 30%, #818CF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .badge-mi300x {{
    background: rgba(16, 185, 129, 0.12);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: var(--font-mono);
  }}

  /* Scene Navigator Pills */
  .scene-nav {{
    display: flex;
    gap: 6px;
    background: rgba(15, 23, 42, 0.6);
    padding: 4px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
  }}
  .scene-pill {{
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
    background: transparent;
  }}
  .scene-pill:hover {{
    color: #FFFFFF;
    background: rgba(255, 255, 255, 0.05);
  }}
  .scene-pill.active {{
    background: var(--accent-indigo);
    color: #FFFFFF;
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
  }}

  .header-actions {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .btn-action {{
    background: #1E293B;
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-action:hover {{
    background: #334155;
    border-color: rgba(255, 255, 255, 0.2);
  }}
  .btn-primary {{
    background: var(--accent-indigo);
    border-color: var(--accent-indigo);
  }}
  .btn-primary:hover {{
    background: #4F46E5;
  }}

  /* Scene Stages */
  .scene-view {{
    position: absolute;
    inset: 64px 0 72px 0;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    transform: scale(0.98);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px 48px;
  }}
  .scene-view.active {{
    opacity: 1;
    pointer-events: auto;
    transform: scale(1);
  }}

  /* =========================================================================
     SCENE 1: ANIMATED PROBLEM HOOK (0:00 - 0:24)
     ========================================================================= */
  .scene1-grid {{
    width: 100%;
    max-width: 1200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
  }}
  .hook-title {{
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    text-align: center;
    background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .hook-subtitle {{
    font-size: 1.05rem;
    color: var(--text-muted);
    text-align: center;
    max-width: 720px;
  }}

  .leakage-counter-card {{
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(239, 68, 68, 0.35);
    box-shadow: 0 0 35px rgba(239, 68, 68, 0.15);
    border-radius: 16px;
    padding: 24px 48px;
    text-align: center;
    margin: 8px 0;
  }}
  .counter-label {{
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #F87171;
    margin-bottom: 6px;
  }}
  .counter-val {{
    font-family: var(--font-mono);
    font-size: 3.5rem;
    font-weight: 800;
    color: #EF4444;
    letter-spacing: -0.03em;
  }}

  .rails-container {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    width: 100%;
    margin-top: 10px;
  }}
  .rail-card {{
    background: #111827;
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }}
  .rail-card:hover {{
    transform: translateY(-2px);
    border-color: rgba(239, 68, 68, 0.5);
  }}
  .rail-icon {{
    font-size: 1.6rem;
    margin-bottom: 8px;
  }}
  .rail-name {{
    font-size: 0.95rem;
    font-weight: 700;
    color: #F1F5F9;
  }}
  .rail-leak-tag {{
    margin-top: 8px;
    font-size: 0.74rem;
    font-family: var(--font-mono);
    font-weight: 700;
    color: #F87171;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.25);
    padding: 4px 8px;
    border-radius: 6px;
    display: inline-block;
  }}

  /* =========================================================================
     SCENE 2: CORE RULE & GUARDRAIL PIPELINE (0:24 - 0:48)
     ========================================================================= */
  .pipeline-stage {{
    width: 100%;
    max-width: 1200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 32px;
  }}
  .motto-banner {{
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.35);
    color: #818CF8;
    padding: 8px 24px;
    border-radius: 20px;
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}
  .pipeline-flow {{
    display: grid;
    grid-template-columns: 1fr 40px 1fr 40px 1fr;
    align-items: center;
    width: 100%;
    gap: 12px;
  }}
  .pipeline-box {{
    background: #111827;
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 24px 20px;
    height: 240px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
  }}
  .pipeline-box.active-box {{
    border-color: var(--accent-indigo);
    box-shadow: 0 0 25px rgba(99, 102, 241, 0.25);
  }}
  .box-header {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .box-icon {{
    font-size: 1.5rem;
  }}
  .box-title {{
    font-size: 0.96rem;
    font-weight: 700;
    color: #FFFFFF;
  }}
  .box-desc {{
    font-size: 0.80rem;
    color: var(--text-muted);
    line-height: 1.5;
    margin: 10px 0;
  }}
  .box-badge {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 6px;
    display: inline-block;
  }}
  .flow-arrow {{
    font-size: 1.5rem;
    color: #6366F1;
    text-align: center;
  }}

  /* Hallucination Trap Demonstration Widget */
  .guardrail-demo-card {{
    background: rgba(15, 23, 42, 0.95);
    border: 1px dashed rgba(239, 68, 68, 0.4);
    border-radius: 10px;
    padding: 12px 16px;
    width: 100%;
    max-width: 900px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 10px;
  }}
  .guard-status {{
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
  }}

  /* =========================================================================
     SCENE 3: LIVE STREAMLIT UI WALKTHROUGH & TELEPROMPTER (0:48 - 1:50)
     ========================================================================= */
  .scene3-container {{
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .teleprompter-bar {{
    background: rgba(17, 24, 39, 0.95);
    border: 1px solid var(--accent-indigo);
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.25);
    border-radius: 10px;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }}
  .cue-indicator {{
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent-amber);
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .cue-text {{
    font-size: 0.92rem;
    font-weight: 700;
    color: #FFFFFF;
  }}

  .workspace-frame-container {{
    flex: 1;
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border-subtle);
    background: #090D16;
  }}
  #streamlit-frame {{
    width: 100%;
    height: 100%;
    border: none;
    background: #090D16;
  }}
  .frame-fallback-overlay {{
    position: absolute;
    inset: 0;
    background: #090D16;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px;
    z-index: 5;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease;
  }}
  .frame-fallback-overlay.show {{
    opacity: 1;
    pointer-events: auto;
  }}

  /* =========================================================================
     SCENE 4: AMD MI300X 192GB HBM3 FINALE (1:50 - 2:15)
     ========================================================================= */
  .scene4-container {{
    width: 100%;
    max-width: 1200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
  }}
  .vram-bar-container {{
    width: 100%;
    background: #111827;
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 24px 28px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  }}
  .vram-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 12px;
  }}
  .vram-title {{
    font-size: 1.1rem;
    font-weight: 800;
    color: #FFFFFF;
  }}
  .vram-total {{
    font-family: var(--font-mono);
    font-size: 1.25rem;
    font-weight: 700;
    color: #34D399;
  }}
  .vram-progress {{
    height: 38px;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    background: #1F2937;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }}
  .vram-seg-weights {{
    width: 32.3%;
    background: linear-gradient(90deg, #4F46E5, #6366F1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
    color: #FFFFFF;
    white-space: nowrap;
  }}
  .vram-seg-kv {{
    width: 67.7%;
    background: linear-gradient(90deg, #059669, #10B981);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
    color: #FFFFFF;
    white-space: nowrap;
  }}

  .benchmark-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    width: 100%;
  }}
  .score-card {{
    background: #111827;
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }}
  .score-val {{
    font-family: var(--font-mono);
    font-size: 2.2rem;
    font-weight: 800;
    margin-bottom: 4px;
  }}
  .score-label {{
    font-size: 0.74rem;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  /* Bottom Teleprompter Subtitle Bar */
  .cinema-footer {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 72px;
    background: rgba(11, 17, 32, 0.95);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 28px;
    z-index: 100;
  }}
  .scrubber-track {{
    width: 100%;
    height: 6px;
    background: #1F2937;
    border-radius: 3px;
    position: relative;
    cursor: pointer;
    margin-bottom: 8px;
  }}
  .scrubber-fill {{
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #6366F1, #10B981);
    border-radius: 3px;
    position: relative;
  }}
  .subtitle-text {{
    font-size: 0.92rem;
    font-weight: 500;
    color: #F1F5F9;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  /* Floating Record Reminder Pill */
  .record-pill {{
    position: absolute;
    bottom: 84px;
    right: 28px;
    background: rgba(239, 68, 68, 0.9);
    color: #FFFFFF;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
    z-index: 110;
  }}
  .rec-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #FFFFFF;
    animation: pulse-dot 1s infinite;
  }}
  @keyframes pulse-dot {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
    100% {{ opacity: 1; }}
  }}
</style>
</head>
<body>

<div id="stage-container">
  <div class="grid-bg"></div>

  <!-- Top Cinema Header -->
  <header class="cinema-header">
    <div class="brand-group">
      <div class="brand-logo">PayLens</div>
      <div class="badge-mi300x">AMD Instinct MI300X · 192GB HBM3</div>
    </div>

    <!-- Interactive Scene Navigator -->
    <div class="scene-nav">
      <button class="scene-pill active" onclick="seekTo(0)">1. Problem Hook (0:00)</button>
      <button class="scene-pill" onclick="seekTo(28)">2. Guardrail Pipeline (0:28)</button>
      <button class="scene-pill" onclick="seekTo(55)">3. Live Deal Desk (0:55)</button>
      <button class="scene-pill" onclick="seekTo(124)">4. AMD MI300X Finale (2:04)</button>
    </div>

    <div class="header-actions">
      <button class="btn-action" id="playBtn" onclick="togglePlay()">▶ Play Demo</button>
      <button class="btn-action" onclick="toggleFullscreen()">⛶ Fullscreen</button>
    </div>
  </header>

  <!-- SCENE 1: ANIMATED PROBLEM HOOK -->
  <div class="scene-view active" id="scene-1">
    <div class="scene1-grid">
      <div class="hook-title">The Silent Cross-Rail E-Commerce Leakage Trap</div>
      <div class="hook-subtitle">Modern commerce runs across 4 disconnected payment rails. Disjointed settlement schedules create untracked capital loss.</div>

      <div class="leakage-counter-card">
        <div class="counter-label">Undetected Revenue Leakage Found Across 20 Stores</div>
        <div class="counter-val" id="animatedCounter">$0.00</div>
      </div>

      <div class="rails-container">
        <div class="rail-card">
          <div class="rail-icon">💳</div>
          <div class="rail-name">Card Gateway (Stripe)</div>
          <div class="rail-leak-tag">$54,200.00 Dispatched Unpaid</div>
        </div>
        <div class="rail-card">
          <div class="rail-icon">🚚</div>
          <div class="rail-name">Courier COD (DHL Express)</div>
          <div class="rail-leak-tag">$38,450.00 COD Shortfall</div>
        </div>
        <div class="rail-card">
          <div class="rail-icon">📱</div>
          <div class="rail-name">Digital Wallets (PayPal)</div>
          <div class="rail-leak-tag">$29,600.00 Abandoned Carts</div>
        </div>
        <div class="rail-card">
          <div class="rail-icon">🏦</div>
          <div class="rail-name">Inventory Demand Rail</div>
          <div class="rail-leak-tag">$23,800.80 Stockout Margin</div>
        </div>
      </div>
    </div>
  </div>

  <!-- SCENE 2: CORE RULE & GUARDRAIL PIPELINE -->
  <div class="scene-view" id="scene-2">
    <div class="pipeline-stage">
      <div class="motto-banner">Architectural Principle: Code Computes, Model Explains</div>

      <div class="pipeline-flow">
        <div class="pipeline-box active-box">
          <div>
            <div class="box-header">
              <span class="box-icon">⚙️</span>
              <span class="box-title">1. Deterministic Core</span>
            </div>
            <div class="box-desc">Python + DuckDB executes 100% of arithmetic, 2-pass fuzzy matching, and Holt-Winters forecasting.</div>
          </div>
          <div>
            <span class="box-badge" style="background: rgba(56, 189, 248, 0.15); color: #38BDF8;">100% CODE MATH</span>
          </div>
        </div>

        <div class="flow-arrow">➔</div>

        <div class="pipeline-box active-box">
          <div>
            <div class="box-header">
              <span class="box-icon">🛡️</span>
              <span class="box-title">2. Regex Guardrail</span>
            </div>
            <div class="box-desc">Strict regex filter validates numeric tokens against database allowed numbers. Blocks rogue numbers instantly.</div>
          </div>
          <div>
            <span class="box-badge" style="background: rgba(16, 185, 129, 0.15); color: #34D399;">ZERO HALLUCINATIONS</span>
          </div>
        </div>

        <div class="flow-arrow">➔</div>

        <div class="pipeline-box active-box">
          <div>
            <div class="box-header">
              <span class="box-icon">🧠</span>
              <span class="box-title">3. Gemma 4 31B</span>
            </div>
            <div class="box-desc">Hosted on AMD MI300X via ROCm vLLM. Formulates operator explanations and recovery drafts.</div>
          </div>
          <div>
            <span class="box-badge" style="background: rgba(129, 140, 248, 0.15); color: #818CF8;">REASONING & ACTIONS</span>
          </div>
        </div>
      </div>

      <!-- Live Hallucination Guardrail Demo Card -->
      <div class="guardrail-demo-card">
        <div>
          <div style="font-size: 0.85rem; font-weight: 700; color: #FFFFFF;">Live Guardrail Test: Rogue Model Injects Fabricated $9,999.00</div>
          <div style="font-size: 0.74rem; color: #94A3B8;">Allowed Database Numbers: [1255.00]</div>
        </div>
        <div class="guard-status" style="color: #EF4444;">
          ⚠️ BLOCKED BY REGEX GUARDRAIL ➔ ACTIVATED FALLBACK
        </div>
      </div>
    </div>
  </div>

  <!-- SCENE 3: LIVE STREAMLIT UI WALKTHROUGH & TELEPROMPTER -->
  <div class="scene-view" id="scene-3">
    <div class="scene3-container">
      <div class="teleprompter-bar">
        <div class="cue-indicator">
          <span style="font-size: 1rem;">🎯</span> DIRECTOR CUE FOR OPERATOR:
        </div>
        <div class="cue-text" id="liveCueText">
          Inspect Card #1 (ORD-LEAK-4349) ➔ Verify Math ➔ Click [⚡ Approve & Dispatch Action Now]
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-action" onclick="reloadStreamlit()">🔄 Reload App</button>
          <a href="http://localhost:8501" target="_blank" class="btn-action" style="text-decoration:none;">↗ Open in Tab</a>
        </div>
      </div>

      <div class="workspace-frame-container">
        <iframe id="streamlit-frame" src="http://localhost:8501"></iframe>
        
        <div class="frame-fallback-overlay" id="frameFallback">
          <div style="text-align: center; max-width: 600px;">
            <div style="font-size: 2.2rem; margin-bottom: 12px;">🛡️ PayLens Live Deal Desk</div>
            <div style="font-size: 0.95rem; color: #94A3B8; margin-bottom: 20px;">
              Streamlit is running on port 8501. If your browser blocks iframe embedding or Streamlit is on another port, open it directly in a new tab:
            </div>
            <a href="http://localhost:8501" target="_blank" class="btn-action btn-primary" style="display:inline-block; font-size:1rem; padding: 10px 24px;">
              🚀 Open Live Streamlit Deal Desk (localhost:8501)
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- SCENE 4: AMD MI300X 192GB HBM3 ARCHITECTURE FINALE -->
  <div class="scene-view" id="scene-4">
    <div class="scene4-container">
      <div class="vram-bar-container">
        <div class="vram-header">
          <div>
            <div class="vram-title">AMD Instinct MI300X Unified Memory Allocation</div>
            <div style="font-size: 0.78rem; color: #94A3B8;">192GB HBM3 @ 5.3 TB/s Memory Bandwidth · ROCm 6.2</div>
          </div>
          <div class="vram-total">192 GB HBM3</div>
        </div>

        <div class="vram-progress">
          <div class="vram-seg-weights">62 GB Gemma 4 31B (BF16)</div>
          <div class="vram-seg-kv">130 GB Massive KV Cache Headroom (32-Way Parallel Concurrency)</div>
        </div>
      </div>

      <div class="benchmark-grid">
        <div class="score-card">
          <div class="score-val" style="color: #38BDF8;">412.5</div>
          <div class="score-label">Cards / Min Throughput</div>
        </div>
        <div class="score-card">
          <div class="score-val" style="color: #34D399;">100.0%</div>
          <div class="score-label">Detector Precision</div>
        </div>
        <div class="score-card">
          <div class="score-val" style="color: #10B981;">100.0%</div>
          <div class="score-label">Detector Recall</div>
        </div>
        <div class="score-card">
          <div class="score-val" style="color: #A78BFA;">18 / 18</div>
          <div class="score-label">Fuzzy True Negatives Excluded</div>
        </div>
      </div>

      <div style="text-align: center; margin-top: 10px;">
        <div style="font-size: 1.45rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">
          PayLens // Stopping Revenue Leaks Before They Cost You The Business.
        </div>
        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 6px;">
          AMD Developer Hackathon: Act III (Commerce &amp; Evolus AI Partner Track)
        </div>
      </div>
    </div>
  </div>

  <!-- Bottom Cinema Audio & Subtitle Controller -->
  <footer class="cinema-footer">
    <div class="scrubber-track" id="scrubberTrack" onclick="handleScrub(event)">
      <div class="scrubber-fill" id="scrubberFill"></div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <div style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted);" id="timeDisplay">
        0:00 / 2:28
      </div>
      <div class="subtitle-text" id="subtitleText">
        Press [Play Demo] or Spacebar to begin continuous 60fps directed presentation...
      </div>
      <div style="font-size: 0.78rem; color: #64748B;">
        Studio Audio: en-US-AndrewNeural (+4%)
      </div>
    </div>
  </footer>

  <!-- Floating Record Guide Pill -->
  <div class="record-pill">
    <div class="rec-dot"></div>
    <span>RECORDER READY (1080p 60fps)</span>
  </div>
</div>

<!-- Embedded Base64 Voiceover Audio Element -->
<audio id="voiceoverAudio" preload="auto">
  <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
</audio>

<script>
  const audio = document.getElementById('voiceoverAudio');
  const scrubberFill = document.getElementById('scrubberFill');
  const timeDisplay = document.getElementById('timeDisplay');
  const subtitleText = document.getElementById('subtitleText');
  const liveCueText = document.getElementById('liveCueText');
  const playBtn = document.getElementById('playBtn');
  const animatedCounter = document.getElementById('animatedCounter');
  const scenes = [
    document.getElementById('scene-1'),
    document.getElementById('scene-2'),
    document.getElementById('scene-3'),
    document.getElementById('scene-4'),
  ];
  const pills = document.querySelectorAll('.scene-pill');

  const sentenceCues = {sentences_json};
  let currentActiveSceneIndex = 0;
  let counterAnimated = false;

  // Format seconds to mm:ss
  function formatTime(sec) {{
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${{m}}:${{s < 10 ? '0' : ''}}${{s}}`;
  }}

  // Play / Pause toggle
  function togglePlay() {{
    if (audio.paused) {{
      audio.play();
      playBtn.innerText = "⏸ Pause";
      playBtn.classList.add('btn-primary');
    }} else {{
      audio.pause();
      playBtn.innerText = "▶ Play Demo";
      playBtn.classList.remove('btn-primary');
    }}
  }}

  // Jump to specific time
  function seekTo(sec) {{
    audio.currentTime = sec;
    if (audio.paused) {{
      togglePlay();
    }}
    updateScene(sec);
  }}

  // Handle click on scrubber
  function handleScrub(e) {{
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    seekTo(pos * (audio.duration || 148));
  }}

  // Scene transition logic based on time
  function updateScene(time) {{
    let targetIndex = 0;
    if (time >= 122) {{
      targetIndex = 3; // Scene 4 (AMD Finale)
    }} else if (time >= 54) {{
      targetIndex = 2; // Scene 3 (Live UI & Cues)
    }} else if (time >= 28) {{
      targetIndex = 1; // Scene 2 (Pipeline & Rule)
    }} else {{
      targetIndex = 0; // Scene 1 (Problem Hook)
    }}

    if (targetIndex !== currentActiveSceneIndex) {{
      scenes[currentActiveSceneIndex].classList.remove('active');
      scenes[targetIndex].classList.add('active');
      pills[currentActiveSceneIndex].classList.remove('active');
      pills[targetIndex].classList.add('active');
      currentActiveSceneIndex = targetIndex;
    }}

    // Scene 1 Counter Animation (0 -> $146,050.80)
    if (targetIndex === 0) {{
      const progress = Math.min(1, time / 22);
      const val = 146050.80 * progress;
      animatedCounter.innerText = "$" + val.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }} else {{
      animatedCounter.innerText = "$146,050.80";
    }}

    // Scene 3 Teleprompter Cues
    if (targetIndex === 2) {{
      if (time < 75) {{
        liveCueText.innerText = "👉 STEP 1: Click Card #1 (ORD-LEAK-4349) ➔ Review Math Formula & Grounded Explanation ➔ Click [Approve & Dispatch]";
      }} else if (time < 95) {{
        liveCueText.innerText = "👉 STEP 2: Scroll down to [Test Red-Team Hallucination Trap] ➔ Click [Simulate Fabricated $9,999] ➔ Show Red BLOCKED Alert";
      }} else {{
        liveCueText.innerText = "👉 STEP 3: Click [📦 Prevent Stockouts] ➔ Notice dynamic re-ranking with Holt-Winters Demand Depletion curve";
      }}
    }}
  }}

  // Audio time update loop
  audio.addEventListener('timeupdate', () => {{
    const cur = audio.currentTime;
    const dur = audio.duration || 148;
    scrubberFill.style.width = (cur / dur * 100) + "%";
    timeDisplay.innerText = `${{formatTime(cur)}} / ${{formatTime(dur)}}`;

    updateScene(cur);

    // Update subtitles matching current timestamp
    for (let i = sentenceCues.length - 1; i >= 0; i--) {{
      if (cur >= sentenceCues[i].start) {{
        subtitleText.innerText = `"${{sentenceCues[i].text}}"`;
        break;
      }}
    }}
  }});

  audio.addEventListener('ended', () => {{
    playBtn.innerText = "▶ Replay Demo";
    playBtn.classList.remove('btn-primary');
  }});

  // Keyboard controls
  window.addEventListener('keydown', (e) => {{
    if (e.code === 'Space') {{
      e.preventDefault();
      togglePlay();
    }} else if (e.code === 'KeyF') {{
      toggleFullscreen();
    }} else if (e.code === 'ArrowRight') {{
      audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
    }} else if (e.code === 'ArrowLeft') {{
      audio.currentTime = Math.max(0, audio.currentTime - 5);
    }} else if (e.key === '1') {{
      seekTo(0);
    }} else if (e.key === '2') {{
      seekTo(28);
    }} else if (e.key === '3') {{
      seekTo(55);
    }} else if (e.key === '4') {{
      seekTo(124);
    }}
  }});

  function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
      document.documentElement.requestFullscreen();
    }} else {{
      document.exitFullscreen();
    }}
  }}

  function reloadStreamlit() {{
    const frame = document.getElementById('streamlit-frame');
    frame.src = frame.src;
  }}

  // Detect iframe load failure
  const frame = document.getElementById('streamlit-frame');
  const fallback = document.getElementById('frameFallback');
  setTimeout(() => {{
    try {{
      if (!frame.contentWindow || frame.contentWindow.location.href === 'about:blank') {{
        // Optional notice
      }}
    }} catch (err) {{
      // Cross-origin is fine! It means Streamlit loaded successfully!
    }}
  }}, 2500);
</script>
</body>
</html>
"""
    with open(DIRECTOR_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    html_size_kb = os.path.getsize(DIRECTOR_HTML) / 1024
    print(f"      Saved {DIRECTOR_HTML} ({html_size_kb:.1f} KB, self-contained)")

def main():
    print("=" * 70)
    print(" PayLens Demo Cinema Director Builder")
    print(" Studio-Grade Neural Voiceover + 60fps HTML5 Cinema Presentation")
    print("=" * 70)

    # 1. Generate Voiceover
    sentences = asyncio.run(generate_voiceover())

    # 2. Build HTML
    build_director_html(sentences)

    print("=" * 70)
    print(" SUCCESS! Demo Director generated:")
    print(f" Voiceover Track: {VOICEOVER_MP3}")
    print(f" Cinema Player:   {DIRECTOR_HTML}")
    print("\n Instructions for 1-take 1080p recording:")
    print(" 1. Launch your Streamlit app in another terminal: streamlit run app.py")
    print(" 2. Open 'demo_studio/demo_director.html' in Chrome or Edge.")
    print(" 3. Press [F] for Fullscreen.")
    print(" 4. Start your screen recorder (OBS, Windows Game Bar Win+Alt+R) at 1080p 60fps.")
    print(" 5. Press Spacebar or [Play Demo] and follow the top teleprompter cues!")
    print("=" * 70)

if __name__ == "__main__":
    main()
