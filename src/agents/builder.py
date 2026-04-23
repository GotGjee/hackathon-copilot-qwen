"""
Builder Agent (Kai) - Senior Developer
Generates skeleton Python/FastAPI code for hackathon projects.
Focuses on function signatures, TODO comments, and project structure
rather than complete implementations.
"""

from typing import List
from pydantic import BaseModel, Field
from loguru import logger

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient


class CodeFileResult(BaseModel):
    """Single code file result."""
    filepath: str
    description: str
    content: str
    language: str = "python"


class BuilderResult(BaseModel):
    """Result from the Builder agent."""
    message: str
    code_files: List[CodeFileResult] = Field(default_factory=list)
    closing_message: str


class BuilderAgent(BaseAgent):
    """Kai - Senior Developer: Generates skeleton code structure."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "builder")

    @staticmethod
    def _parse_raw_files(raw_text: str, title: str) -> List[dict]:
        """
        Parse raw text response into code files.
        Expected format:
        ---BEGIN FILE: filepath ---
        description: description here
        ```language
        code content here
        ```
        ---END FILE---
        """
        import re
        code_files = []
        
        # Pattern 1: ---BEGIN FILE: filepath --- ... ---END FILE---
        file_pattern = re.compile(
            r'---BEGIN FILE:\s*(.+?)---\s*\n'
            r'description:\s*(.+?)\s*\n'
            r'```(\w*)\s*\n'
            r'([\s\S]*?)'
            r'```\s*\n'
            r'---END FILE---',
            re.MULTILINE
        )
        
        for match in file_pattern.finditer(raw_text):
            code_files.append({
                "filepath": match.group(1).strip(),
                "description": match.group(2).strip(),
                "content": match.group(4).rstrip(),
                "language": match.group(3).strip() or "python"
            })
        
        # Pattern 2: # File: filepath with code blocks
        if not code_files:
            block_pattern = re.compile(
                r'#\s*(?:File|FILE):\s*(.+?)\n'
                r'```(\w*)\s*\n'
                r'([\s\S]*?)'
                r'```',
                re.MULTILINE
            )
            for match in block_pattern.finditer(raw_text):
                code_files.append({
                    "filepath": match.group(1).strip(),
                    "description": f"Generated file: {match.group(1).strip()}",
                    "content": match.group(3).rstrip(),
                    "language": match.group(2).strip() or "python"
                })
        
        # Pattern 3: Just code blocks with filepath on first line
        if not code_files:
            simple_pattern = re.compile(
                r'```(\w*)\s+(.+?)\n([\s\S]*?)```',
                re.MULTILINE
            )
            for match in simple_pattern.finditer(raw_text):
                code_files.append({
                    "filepath": match.group(2).strip(),
                    "description": f"Generated file: {match.group(2).strip()}",
                    "content": match.group(3).rstrip(),
                    "language": match.group(1).strip() or "python"
                })
        
        return code_files

    async def generate_code(
        self,
        title: str,
        architecture: dict,
        files_list: List[str],
        constraints: str,
    ) -> BuilderResult:
        """Generate skeleton code files for the hackathon project."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            title=title,
            architecture=str(architecture),
            files_list=str(files_list),
            constraints=constraints,
        )

        from src.core.json_parser import StructuredOutputParser
        
        # Method 1: Use XML-style tags (more reliable than JSON for code)
        system_content = (
            "You are Kai, a senior developer creating SKELETON CODE for: " + title + "\n\n"
            "Create skeleton code with function signatures and TODO comments.\n"
            "DO NOT write complete implementations - just the structure!\n\n"
            "Respond using this EXACT format (use XML-style tags, NOT JSON):\n\n"
            "<message>\n"
            "Your opening message here\n"
            "</message>\n\n"
            "<file>\n"
            "<path>path/to/file1.py</path>\n"
            "<description>Description of this file</description>\n"
            "<language>python</language>\n"
            "<code>\n"
            "# Skeleton code with TODOs\n"
            "# TODO: implement this function\n"
            "def my_function(param: str) -> str:\n"
            "    \"\"\"Process the input and return result.\"\"\"\n"
            "    pass\n"
            "</code>\n"
            "</file>\n\n"
            "<file>\n"
            "<path>README.md</path>\n"
            "<description>Comprehensive project README with overview, features, architecture, setup, and TODOs</description>\n"
            "<language>markdown</language>\n"
            "<code>\n"
            "# Project Title\n"
            "> Generated by Hackathon Copilot | Session: xxx | Date: xxxx-xx-xx\n\n"
            "## Project Overview\n"
            "2-3 paragraphs explaining what the project does, problem it solves, target users\n\n"
            "## Key Features\n"
            "- Feature 1: description\n"
            "- Feature 2: description\n\n"
            "## Architecture\n"
            "Brief summary + tech stack table\n\n"
            "## Getting Started\n"
            "Prerequisites, installation steps, env variables\n\n"
            "## What's Implemented vs TODO\n"
            "Checklist of completed items and prioritized TODOs\n\n"
            "## Hackathon Strategy\n"
            "MVP scope, next steps, tips for success\n\n"
            "## API Reference\n"
            "Table of main endpoints\n\n"
            "## Testing\n"
            "How to run tests\n"
            "</code>\n"
            "</file>\n\n"
            "<closing>\n"
            "Your closing message here\n"
            "</closing>\n\n"
            "IMPORTANT RULES:\n"
            "- Use XML-style tags exactly as shown\n"
            "- Put ALL code inside <code> tags\n"
            "- Use single quotes in Python code to avoid escaping issues\n"
            "- Create SKELETON code with TODOs, not complete implementations\n"
            "- Include a README.md file explaining what participants need to do\n"
            "- Do NOT include any other text outside the tags"
        )
        xml_messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            raw_response = await self.api_client.chat_completion(
                messages=xml_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=max(self.max_tokens, 12000),  # More tokens for skeleton
            )
            
            code_files_data = self._parse_xml_response(raw_response, title)
            
            if code_files_data:
                # Extract message and closing from response
                message = self._extract_xml_text(raw_response, "message") or "Skeleton code generated successfully"
                closing = self._extract_xml_text(raw_response, "closing") or "Please review the skeleton structure."
                
                logger.info(f"Builder parsed {len(code_files_data)} skeleton files (XML mode)")
                return BuilderResult(
                    message=message,
                    code_files=[CodeFileResult(**cf) for cf in code_files_data],
                    closing_message=closing,
                )
        except Exception as e:
            logger.warning(f"Builder XML mode failed: {e}, trying JSON retry")
        
        # Method 2: Try JSON format as fallback
        json_messages = self._build_messages(system_prompt, user_prompt)
        json_messages.append({
            "role": "user",
            "content": (
                "Respond with ONLY a valid JSON object. No markdown, no explanations.\n"
                '{"message": "...", "code_files": [{"filepath": "...", "description": "...", "content": "...", "language": "..."}], "closing_message": "..."}'
            )
        })
        
        try:
            raw_response = await self.api_client.chat_completion(
                messages=json_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=max(self.max_tokens, 12000),
                response_format="json_object",
            )
            data = StructuredOutputParser.parse_dict(raw_response)
            code_files_data = data.get("code_files", [])
            if code_files_data:
                logger.info(f"Builder parsed {len(code_files_data)} skeleton files (JSON mode)")
                return BuilderResult(
                    message=data.get("message", ""),
                    code_files=[CodeFileResult(**cf) for cf in code_files_data if "filepath" in cf and "content" in cf],
                    closing_message=data.get("closing_message", ""),
                )
        except Exception as e:
            logger.warning(f"Builder JSON mode failed: {e}, trying raw text mode")
        
        # Method 3: Raw text format with code blocks
        raw_messages = [
            {"role": "system", "content": f"You are Kai, a senior developer creating SKELETON CODE for: {title}\n\nRespond with code blocks in this format:\n---BEGIN FILE: path/to/file.py---\ndescription: description here\n```python\n# skeleton code with TODOs here\n```\n---END FILE---"},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            raw_response = await self.api_client.chat_completion(
                messages=raw_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=max(self.max_tokens, 12000),
            )
            
            code_files_data = self._parse_raw_files(raw_response, title)
            
            if code_files_data:
                logger.info(f"Builder parsed {len(code_files_data)} skeleton files (raw mode)")
                return BuilderResult(
                    message="Skeleton code generated successfully",
                    code_files=[CodeFileResult(**cf) for cf in code_files_data],
                    closing_message="Please review the skeleton structure.",
                )
        except Exception as e:
            logger.warning(f"Builder raw mode failed: {e}, using fallback")
        
        # Fallback - Create basic skeleton structure
        logger.error("All Builder methods failed, using fallback")
        title_safe = title if title else "Project"
        return BuilderResult(
            message=f"Skeleton code for {title_safe} - fallback mode",
            code_files=[
                CodeFileResult(
                    filepath="README.md",
                    description="Project README for hackathon participants",
                    content=f"""# {title_safe}
> Generated by Hackathon Copilot | Fallback Mode

## 📌 Project Overview
{title_safe} is a hackathon project designed to solve a specific problem. This README provides a comprehensive guide to understanding, setting up, and extending this project.

**What this project does:**
This is a skeleton project generated by AI. It provides the basic structure, API routes, and type definitions to get you started quickly.

**Who it's for:**
Hackathon participants who need a solid starting point and want to focus on implementing core business logic rather than boilerplate setup.

## ✨ Key Features
- **API Skeleton**: Pre-defined route structure with FastAPI
- **Type Safety**: Pydantic models for data validation
- **Modular Architecture**: Clean separation of concerns
- **Hackathon Ready**: TODO-driven development approach

## 🏗️ Architecture
This project follows a modular architecture with clear separation between routes, services, and data models.

### Tech Stack
| Category | Technology |
|----------|------------|
| Backend | FastAPI |
| Data Validation | Pydantic |
| Server | Uvicorn (ASGI) |
| Database | SQLite/PostgreSQL (TBD) |

## 📁 Project Structure
```
project/
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── src/
│   ├── routers/         # API route definitions
│   ├── services/        # Business logic layer
│   └── models/          # Data models and schemas
└── tests/               # Test files
```

## 🚀 Getting Started

### Prerequisites
- Python >= 3.10
- pip (Python package manager)
- (Optional) PostgreSQL database
- API keys for any external services you plan to use

### Installation
```bash
# 1. Clone the repository
git clone <your-repo-url>
cd {title_safe}

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# 5. Run the development server
uvicorn main:app --reload

# 6. Open http://localhost:8000/docs for API documentation
```

### Environment Variables
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Database connection string | No | sqlite:///db.sqlite3 |
| `API_KEY` | External API key | Depends on features | - |

## 📋 What's Implemented vs TODO

### ✅ Implemented
- [x] Project structure and architecture
- [x] API route definitions (skeleton)
- [x] Data models and schemas
- [x] Type hints throughout codebase

### 🔨 TODO (Priority Order)
1. **[HIGH]** Implement core business logic in `src/services/`
   - See TODO comments in each file
   - Connect to database or external APIs as needed
2. **[HIGH]** Complete API endpoint implementations in `src/routers/`
   - Add proper error handling
   - Connect to service layer
3. **[MEDIUM]** Add database models and migrations
4. **[MEDIUM]** Build frontend UI (if applicable)
5. **[LOW]** Write unit and integration tests
6. **[LOW]** Add CI/CD pipeline

Check each source file for `TODO:` comments to find specific implementation tasks.

## 🎯 Hackathon Strategy

### MVP Scope (What to build first)
1. Focus on getting ONE core feature working end-to-end
2. Skip UI polish initially - use API directly or simple forms
3. Get data flowing: Input → Processing → Output

### Next Steps After MVP
1. Add UI/UX polish
2. Implement additional features from TODO list
3. Prepare demo script and pitch deck
4. Write tests for demo-critical paths

### Tips for Success
- Start with skeleton code and fill in TODOs one by one
- Test each feature independently before integration
- Keep scope small - better to have one feature working well than many half-working
- Use the API docs at http://localhost:8000/docs for testing endpoints

## 🧪 Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_main.py
```

## 📊 API Reference
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome page |
| GET | `/health` | Health check endpoint |
| GET | `/docs` | Swagger API documentation |

See `/docs` when running the server for full interactive API documentation.

## 🤝 Contributing / Next Steps
1. Pick a TODO item from the list above
2. Implement the feature following the existing patterns
3. Add tests for your new code
4. Update this README if you add new setup steps

## 📝 License
MIT License

## 🙏 Acknowledgments
- Built with Hackathon Copilot AI assistance
- Powered by FastAPI, Pydantic, and Uvicorn
""",
                    language="markdown"
                ),
                CodeFileResult(
                    filepath="main.py",
                    description="FastAPI application entry point",
                    content=f"""from fastapi import FastAPI

app = FastAPI(title='{title_safe}')


@app.get('/')
async def root():
    '''Root endpoint.'''
    # TODO: Add welcome page or API documentation
    return {{'message': 'Welcome to {title_safe}'}}


@app.get('/health')
async def health():
    '''Health check endpoint.'''
    # TODO: Add database health check
    return {{'status': 'ok'}}


# TODO: Add more endpoints here
# See architecture document for API routes
""",
                    language="python"
                ),
                CodeFileResult(
                    filepath="requirements.txt",
                    description="Project dependencies",
                    content="fastapi\nuvicorn\npydantic\n",
                    language="text"
                )
            ],
            closing_message=f"Created basic skeleton for {title_safe}. Start implementing the TODOs!",
        )

    @staticmethod
    def _parse_xml_response(raw_text: str, title: str) -> List[dict]:
        """Parse XML-style response into code files."""
        import re
        code_files = []
        
        # Pattern: <file>...</file> blocks
        file_pattern = re.compile(
            r'<file>(.*?)</file>',
            re.DOTALL
        )
        
        for file_match in file_pattern.finditer(raw_text):
            file_content = file_match.group(1)
            
            path_match = re.search(r'<path>(.*?)</path>', file_content, re.DOTALL)
            desc_match = re.search(r'<description>(.*?)</description>', file_content, re.DOTALL)
            lang_match = re.search(r'<language>(.*?)</language>', file_content, re.DOTALL)
            code_match = re.search(r'<code>(.*?)</code>', file_content, re.DOTALL)
            
            if path_match and code_match:
                code_files.append({
                    "filepath": path_match.group(1).strip(),
                    "description": desc_match.group(1).strip() if desc_match else f"Generated file: {path_match.group(1).strip()}",
                    "content": code_match.group(1).rstrip('\n'),
                    "language": lang_match.group(1).strip() if lang_match else "python"
                })
        
        return code_files

    @staticmethod
    def _extract_xml_text(text: str, tag: str) -> str:
        """Extract text content from XML-style tag."""
        import re
        match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""