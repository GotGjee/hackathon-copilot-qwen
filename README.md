# 🚀 Hackathon Copilot

> **AI-Powered Multi-Agent System for Hackathon Success**

An Agentic Multi-Agent system that takes a "Hackathon Theme" and "Constraints" as input and produces:
- ✅ A validated project idea
- ✅ A functional code prototype skeleton
- ✅ A pitch presentation package

## 🎯 Features

- **🧠 AI Team Simulation**: 7 AI agents with distinct personalities working together
- **⚖️ Judge Evaluation**: Multi-criteria scoring for idea validation
- **🔨 Code Generation**: Automated code skeleton creation with self-correction
- **🎤 Pitch Assistant**: Slide outlines and speaker scripts
- **👥 Human-in-the-Loop**: Interactive checkpoints for human review
- **📦 Export**: Download code as ZIP, pitch as text

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     🖥️  Streamlit Frontend                   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP / WebSocket
┌────────────────────────────▼────────────────────────────────┐
│                    🚀  FastAPI Backend                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Orchestrator                           │ │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │ │
│  │  │ Layer 1 │─▶│ Layer 2  │─▶│ Layer 3  │─▶│Export  │ │ │
│  │  │Ideation │  │ Build    │  │ Pitch    │  │        │ │ │
│  │  │+ Judge  │  │+ Critic  │  │+ Script  │  │        │ │ │
│  │  └─────────┘  └──────────┘  └──────────┘  └────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  │
│  │   State Manager         │  │   API Client (Qwen)      │  │
│  │   (JSON + In-Memory)    │  │   (Async + Retry)        │  │
│  └─────────────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🎭 AI Agents

| Agent | Name | Role | Personality |
|-------|------|------|-------------|
| 🧠 Ideator | Max | Creative Director | Excited, creative, always brainstorming |
| ⚖️ Judge | Sarah | Pragmatic Lead | Analytical, logical, focuses on feasibility |
| 📋 Planner | Dave | Project Manager | Deadline-driven, organized |
| 🏗️ Architect | Luna | Tech Lead | Big-picture thinker, design patterns |
| 🔨 Builder | Kai | Senior Developer | Fast coder, loves clever hacks |
| 🔍 Critic | Rex | QA Lead | Skeptical, detail-oriented, finds every bug |
| 🎤 Pitch | Nova | Storyteller | Charismatic, compelling narratives |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Qwen API access

### Installation

```bash
# Clone or navigate to the project
cd hackathon-copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API key
```

### Running

```bash
# Start the backend (FastAPI)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Start the frontend (Streamlit) - in another terminal
streamlit run src.frontend/app.py
```

Open your browser to `http://localhost:8501`

## 📁 Project Structure

```
hackathon-copilot/
├── README.md
├── requirements.txt
├── .env.example
├── prompts/                    # YAML prompt templates
│   ├── ideator.yaml
│   ├── judge.yaml
│   ├── planner.yaml
│   ├── architect.yaml
│   ├── builder.yaml
│   ├── critic.yaml
│   ├── pitch_strategist.yaml
│   ├── slide_agent.yaml
│   └── script_agent.yaml
├── config/
│   └── agents.yaml             # Agent personalities & configs
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings & env vars
│   ├── core/
│   │   ├── state.py            # Pydantic state machine
│   │   ├── orchestrator.py     # Workflow orchestration
│   │   ├── api_client.py       # Async Qwen API wrapper
│   │   └── json_parser.py      # Structured output enforcement
│   ├── agents/
│   │   ├── base.py             # Base agent class
│   │   ├── ideator.py
│   │   ├── judge.py
│   │   ├── planner.py
│   │   ├── architect.py
│   │   ├── builder.py
│   │   ├── critic.py
│   │   ├── pitch_strategist.py
│   │   ├── slide_agent.py
│   │   └── script_agent.py
│   ├── services/
│   │   ├── state_manager.py    # JSON + cache persistence
│   │   ├── session_service.py  # Session CRUD
│   │   └── export_service.py   # ZIP generation
│   └── models/
│       ├── schemas.py          # Pydantic request/response models
│       └── states.py           # Session state models
├── api/
│   └── routes.py               # API endpoints
├── ui/
│   └── app.py                  # Streamlit frontend
├── data/                       # Runtime data storage
│   ├── sessions/               # Session JSON files
│   └── exports/                # Generated ZIP files
└── tests/
    ├── test_state.py
    ├── test_orchestrator.py
    └── test_agents.py
```

## 🔧 Configuration

### Environment Variables

```env
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://api.qwen.ai/v1
DEFAULT_MODEL=qwen3.6-plus
CODE_MODEL=qwen3-coder-plus
```

### Agent Config

Edit `config/agents.yaml` to customize agent personalities and system prompts.

## 📝 Usage

1. **Input Theme & Constraints**: Enter your hackathon theme and any constraints
2. **Wait for Ideation**: AI agents generate and evaluate ideas
3. **Select Idea**: Review scored ideas and pick your favorite
4. **Wait for Code Generation**: Agents plan, architect, and build code
5. **Review Code**: Check generated code and request changes
6. **Get Pitch Package**: Receive slide outline and speaker script
7. **Export**: Download code as ZIP and pitch materials

## 🎬 Demo Strategy

For hackathon presentations:
1. Use the built-in agent chat log for "wow factor"
2. Export code as ZIP to show working prototype
3. Use slide outline + script for Canva presentations
4. Record demo videos instead of live demos

## 🛠️ Tech Stack

- **Backend**: FastAPI (Async)
- **Frontend**: Streamlit
- **Data Validation**: Pydantic
- **AI Models**: Qwen API (qwen3.6-plus, qwen3-coder-plus)
- **Storage**: JSON + In-Memory Cache

## 📄 License

MIT License

---

Built with GotGjee❤️ for Your Hackathon!!