"""
Hackathon Copilot - Streamlit Frontend
Card-style design that works beautifully within Streamlit's natural padding.
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime
from typing import Optional

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

AGENTS = {
    "สุรเดช": {"icon": "🧠", "color": "#FF6B00", "bg": "#FFF3E0"},
    "วันเพ็ญ": {"icon": "⚖️", "color": "#E65100", "bg": "#FFF8E1"},
    "สมศักดิ์": {"icon": "📋", "color": "#F57C00", "bg": "#FFFDE7"},
    "พิมพ์ใจ": {"icon": "🏗️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "ธนภัทร": {"icon": "🔨", "color": "#EF6C00", "bg": "#FBE9E7"},
    "วิชัย": {"icon": "🔍", "color": "#BF360C", "bg": "#FFCCBC"},
    "อรุณี": {"icon": "🎤", "color": "#FF6B00", "bg": "#FFF3E0"},
    "อรุณี (Slides)": {"icon": "📊", "color": "#E65100", "bg": "#FFF8E1"},
    "อรุณี (Script)": {"icon": "🎙️", "color": "#FF8F00", "bg": "#FFF3E0"},
    "System": {"icon": "🚀", "color": "#999", "bg": "#F5F5F5"},
}

CSS = """
<style>
/* Hide defaults */
[data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
.main { background: #F5F0EB !important; }
.main .block-container { 
    max-width: 800px !important; 
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* File Tree View */
.file-tree {
    background: #1E1E1E;
    border-radius: 12px;
    padding: 16px;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    font-size: 0.8rem;
    max-height: 400px;
    overflow-y: auto;
}
.file-tree::-webkit-scrollbar {
    width: 8px;
}
.file-tree::-webkit-scrollbar-track {
    background: #1E1E1E;
}
.file-tree::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}
.tree-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #888;
    font-size: 0.75rem;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #333;
}
.tree-item {
    display: flex;
    align-items: center;
    padding: 6px 10px;
    margin: 2px 0;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
    color: #CCC;
    gap: 8px;
}
.tree-item:hover {
    background: #2D2D2D;
    color: #FFB74D;
}
.tree-item.selected {
    background: #2D2D2D;
    color: #FF8F00;
}
.tree-icon {
    font-size: 1rem;
    flex-shrink: 0;
}
.tree-folder {
    color: #81C784;
}
.tree-file {
    color: #64B5F6;
}
.tree-file-md {
    color: #B39DDB;
}
.tree-file-yaml {
    color: #FFB74D;
}
.tree-file-txt {
    color: #90A4AE;
}
.tree-indent {
    width: 20px;
    flex-shrink: 0;
}

/* Code Block with Syntax Highlighting */
.code-viewer {
    background: #1E1E1E;
    border-radius: 12px;
    overflow: hidden;
    margin: 12px 0;
}
.code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #2D2D2D;
    padding: 10px 16px;
    border-bottom: 1px solid #333;
}
.code-filename {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: #CCC;
}
.code-lang-badge {
    background: #FF6B00;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
}
.code-body {
    padding: 16px;
    overflow-x: auto;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    font-size: 0.8rem;
    line-height: 1.6;
    color: #D4D4D4;
    max-height: 500px;
    overflow-y: auto;
    white-space: pre;
    tab-size: 4;
}
.code-body::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
.code-body::-webkit-scrollbar-track {
    background: #1E1E1E;
}
.code-body::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}

/* Syntax Highlighting (VS Code Dark+ Theme) */
.syn-keyword { color: #569CD6; }
.syn-string { color: #CE9178; }
.syn-comment { color: #6A9955; font-style: italic; }
.syn-number { color: #B5CEA8; }
.syn-function { color: #DCDCAA; }
.syn-class { color: #4EC9B0; }
.syn-decorator { color: #DCDCAA; }
.syn-type { color: #4EC9B0; }
.syn-operator { color: #D4D4D4; }
.syn-punctuation { color: #808080; }
.syn-boolean { color: #569CD6; }
.syn-import { color: #C586C0; }
.syn-self { color: #569CD6; font-style: italic; }
.syn-markdown-h1 { color: #569CD6; font-weight: bold; }
.syn-markdown-h2 { color: #569CD6; font-weight: bold; }
.syn-markdown-h3 { color: #569CD6; font-weight: bold; }
.syn-markdown-link { color: #4EC9B0; }
.syn-markdown-code { color: #CE9178; }
.syn-yaml-key { color: #569CD6; }
.syn-yaml-value { color: #CE9178; }

/* File Stats Bar */
.file-stats {
    display: flex;
    gap: 16px;
    padding: 8px 16px;
    background: #2D2D2D;
    border-top: 1px solid #333;
    font-size: 0.7rem;
    color: #888;
}

/* Create page card */
.create-card {
    background: white;
    border-radius: 24px;
    box-shadow: 0 4px 24px rgba(255,107,0,0.08);
    padding: 2.5rem;
    text-align: center;
    margin: 2rem 0;
}

/* Chat container */
.chat-container {
    background: white;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    overflow: hidden;
    margin-bottom: 1rem;
}

/* Header inside chat */
.chat-hdr {
    background: linear-gradient(135deg, #FF6B00, #FF8F00);
    color: white;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Progress */
.pbar-wrap {
    background: #FFF3E0;
    padding: 0;
}

/* Messages area */
.msgs {
    padding: 12px;
    background: #FAFAFA;
    max-height: 55vh;
    overflow-y: auto;
}

/* Bubble styles */
.msg {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
    align-items: flex-start;
}
.ava {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0; margin-top: 2px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.bub-body { flex: 1; min-width: 0; }
.bub-name { font-size: 0.72rem; font-weight: 700; margin-bottom: 3px; }
.bub {
    padding: 10px 14px;
    border-radius: 18px;
    border-top-left-radius: 6px;
    font-size: 0.85rem;
    line-height: 1.55;
    word-wrap: break-word;
    white-space: pre-wrap;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.bub-time { font-size: 0.6rem; color: #BBB; margin-top: 3px; }

/* System messages */
.sys {
    text-align: center;
    padding: 6px 14px;
    margin: 10px auto;
    font-size: 0.72rem;
    color: #999;
    background: #F5F5F5;
    border-radius: 14px;
    max-width: 65%;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #FF6B00, #FF8F00) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    box-shadow: 0 2px 8px rgba(255,107,0,0.2) !important;
}
.stButton > button:hover {
    box-shadow: 0 4px 12px rgba(255,107,0,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 14px !important;
    border: 2px solid #FFD180 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #FF6B00 !important;
    box-shadow: 0 0 0 3px rgba(255,107,0,0.1) !important;
}

/* Idea cards */
.idea-card {
    background: white;
    border-radius: 16px;
    border: 2px solid #FFE0B2;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.idea-card:hover {
    border-color: #FF6B00;
    box-shadow: 0 4px 12px rgba(255,107,0,0.1);
}

/* Bottom bar */
.bot-bar {
    display: flex;
    gap: 8px;
    padding: 12px 0;
}

/* JSON Code Block Styling */
.json-code-block {
    background: #1E1E1E !important;
    border-radius: 12px !important;
    padding: 16px !important;
    margin: 12px 0 !important;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace !important;
    font-size: 0.78rem !important;
    color: #D4D4D4 !important;
    overflow-x: auto !important;
    max-height: 400px !important;
    overflow-y: auto !important;
    line-height: 1.5 !important;
    white-space: pre !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    border: 1px solid #333 !important;
}

.json-code-block::-webkit-scrollbar {
    width: 8px !important;
    height: 8px !important;
}

.json-code-block::-webkit-scrollbar-track {
    background: #1E1E1E !important;
}

.json-code-block::-webkit-scrollbar-thumb {
    background: #444 !important;
    border-radius: 4px !important;
}

/* JSON header label */
.json-label {
    display: inline-block;
    background: #FF6B00 !important;
    color: white !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    margin-bottom: 8px !important;
}
</style>
"""


def api(method, ep, data=None):
    try:
        url = f"{API_BASE_URL}{ep}"
        r = requests.get(url, timeout=6) if method == "GET" else requests.post(url, json=data or {}, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def ftime():
    return datetime.now().strftime("%H:%M")


# Language extensions mapping for syntax highlighting
LANG_EXT = {
    ".py": "python", ".pyi": "python",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".html": "html", ".css": "css", ".scss": "css",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".txt": "text",
    ".sql": "sql", ".sh": "bash",
    ".toml": "toml", ".env": "text",
    ".dockerfile": "dockerfile",
}


def get_language_from_path(filepath: str) -> str:
    """Get language from file extension."""
    if filepath.endswith(".dockerfile"):
        return "dockerfile"
    ext = os.path.splitext(filepath)[1].lower()
    return LANG_EXT.get(ext, "text")


def highlight_python(code: str) -> str:
    """Simple Python syntax highlighting."""
    import re
    lines = code.split('\n')
    result = []
    for line in lines:
        hl = line
        # Comments
        hl = re.sub(r'(#.+)$', r'<span class="syn-comment">\1</span>', hl)
        # Strings (triple quotes, double quotes, single quotes)
        hl = re.sub(r'(""".*?"""|\'\'\'.*?\'\'\')', r'<span class="syn-string">\1</span>', hl)
        hl = re.sub(r'("(?:[^"\\]|\\.)*")', r'<span class="syn-string">\1</span>', hl)
        hl = re.sub(r"('(?:[^'\\]|\\.)*')", r'<span class="syn-string">\1</span>', hl)
        # f-strings
        hl = re.sub(r'(f"(?:[^"\\]|\\.)*")', r'<span class="syn-string">\1</span>', hl)
        hl = re.sub(r"(f'(?:[^'\\]|\\.)*')", r'<span class="syn-string">\1</span>', hl)
        # Keywords
        for kw in ['def ', 'class ', 'import ', 'from ', 'return ', 'async ', 'await ',
                    'if ', 'elif ', 'else ', 'for ', 'while ', 'try:', 'except ', 'finally:',
                    'with ', 'yield ', 'raise ', 'pass', 'break ', 'continue ',
                    'True', 'False', 'None', 'and ', 'or ', 'not ', 'in ', 'is ',
                    'lambda ', 'global ', 'nonlocal ']:
            if kw.endswith(' '):
                hl = hl.replace(kw, f'<span class="syn-keyword">{kw}</span>')
        # Decorators
        hl = re.sub(r'(@\w+)', r'<span class="syn-decorator">\1</span>', hl)
        # self
        hl = re.sub(r'\bself\b', r'<span class="syn-self">self</span>', hl)
        # Function calls
        hl = re.sub(r'(\w+)(\()', r'<span class="syn-function">\1</span>\2', hl)
        result.append(hl)
    return '\n'.join(result)


def highlight_typescript(code: str) -> str:
    """Simple TypeScript/JavaScript syntax highlighting."""
    import re
    lines = code.split('\n')
    result = []
    for line in lines:
        hl = line
        # Comments
        hl = re.sub(r'(//.+)$', r'<span class="syn-comment">\1</span>', hl)
        hl = re.sub(r'(/\*.*?\*/)', r'<span class="syn-comment">\1</span>', hl)
        # Strings
        hl = re.sub(r'(`[^`]*`)', r'<span class="syn-string">\1</span>', hl)
        hl = re.sub(r'("(?:[^"\\]|\\.)*")', r'<span class="syn-string">\1</span>', hl)
        hl = re.sub(r"('(?:[^'\\]|\\.)*')", r'<span class="syn-string">\1</span>', hl)
        # Keywords
        for kw in ['import ', 'from ', 'export ', 'const ', 'let ', 'var ', 'function ',
                    'async ', 'await ', 'return ', 'if ', 'else ', 'for ', 'while ',
                    'class ', 'interface ', 'type ', 'extends ', 'implements ',
                    'new ', 'this', 'throw ', 'try ', 'catch ', 'finally ',
                    'switch ', 'case ', 'break ', 'default ', 'true', 'false', 'null',
                    'undefined', 'void ', 'typeof ', 'instanceof ']:
            if kw.endswith(' '):
                hl = hl.replace(kw, f'<span class="syn-keyword">{kw}</span>')
        # Function calls
        hl = re.sub(r'(\w+)(\()', r'<span class="syn-function">\1</span>\2', hl)
        result.append(hl)
    return '\n'.join(result)


def highlight_markdown(code: str) -> str:
    """Simple Markdown syntax highlighting."""
    import re
    lines = code.split('\n')
    result = []
    for line in lines:
        hl = line
        # Headers
        hl = re.sub(r'^(#{1,6})\s+(.+)$', r'<span class="syn-markdown-h1">\1 \2</span>', hl)
        # Links
        hl = re.sub(r'(\[.+?\])(\(.+?\))', r'<span class="syn-markdown-link">\1</span>\2', hl)
        # Inline code
        hl = re.sub(r'(`.+?`)', r'<span class="syn-markdown-code">\1</span>', hl)
        # Bold/Italic
        hl = re.sub(r'(\*\*.*?\*\*)', r'<strong>\1</strong>', hl)
        result.append(hl)
    return '\n'.join(result)


def highlight_yaml(code: str) -> str:
    """Simple YAML syntax highlighting."""
    import re
    lines = code.split('\n')
    result = []
    for line in lines:
        hl = line
        # Comments
        hl = re.sub(r'(#.+)$', r'<span class="syn-comment">\1</span>', hl)
        # Keys
        hl = re.sub(r'^(\s*)([\w_]+)(:)', r'\1<span class="syn-yaml-key">\2</span><span class="syn-punctuation">\3</span>', hl)
        # String values after colon
        hl = re.sub(r'(:\s+)(.+)$', r'\1<span class="syn-yaml-value">\2</span>', hl)
        result.append(hl)
    return '\n'.join(result)


def highlight_code(code: str, language: str) -> str:
    """Apply syntax highlighting based on language."""
    if language in ('python', 'py'):
        return highlight_python(code)
    elif language in ('typescript', 'javascript', 'ts', 'tsx', 'js', 'jsx'):
        return highlight_typescript(code)
    elif language == 'markdown':
        return highlight_markdown(code)
    elif language in ('yaml', 'yml', 'toml'):
        return highlight_yaml(code)
    else:
        # Escape HTML for other languages
        import html
        return html.escape(code)


def get_file_icon(filepath: str) -> tuple:
    """Get icon and class for a file based on extension."""
    ext = os.path.splitext(filepath)[1].lower()
    icons = {
        ".py": ("🐍", "tree-file"),
        ".ts": ("📘", "tree-file"),
        ".tsx": ("⚛️", "tree-file"),
        ".js": ("📜", "tree-file"),
        ".html": ("🌐", "tree-file"),
        ".css": ("🎨", "tree-file"),
        ".json": ("📋", "tree-file"),
        ".yaml": ("⚙️", "tree-file-yaml"),
        ".yml": ("⚙️", "tree-file-yaml"),
        ".md": ("📝", "tree-file-md"),
        ".txt": ("📄", "tree-file-txt"),
        ".sql": ("🗃️", "tree-file"),
        ".sh": ("🖥️", "tree-file"),
        ".toml": ("⚙️", "tree-file-yaml"),
        ".env": ("🔐", "tree-file-txt"),
        ".dockerfile": ("🐳", "tree-file"),
    }
    return icons.get(ext, ("📄", "tree-file"))


def build_file_tree(code_artifacts: dict, selected_file: Optional[str] = None) -> str:
    """Build a file tree view HTML from code artifacts."""
    if not code_artifacts:
        return '<div style="text-align:center;color:#666;padding:2rem">📂 No files generated yet</div>'
    
    # Build directory structure
    tree = {}
    for filepath in sorted(code_artifacts.keys()):
        parts = filepath.split('/')
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = filepath  # leaf node
    
    def render_tree(node, path="", indent=0):
        html_parts = []
        for key in sorted(node.keys()):
            value = node[key]
            icon_class = "tree-folder"
            icon = "📁"
            is_leaf = isinstance(value, str)
            
            if is_leaf:
                icon, icon_class = get_file_icon(key)
                if value == selected_file:
                    icon_class += " selected"
                file_path_attr = f'data-file="{value}"'
                click_handler = f'onclick="selectFile(\'{value}\')"'
                html_parts.append(
                    f'<div class="tree-item {icon_class}" {file_path_attr} {click_handler} style="padding-left:{10 + indent*20}px">'
                    f'<span class="tree-icon">{icon}</span>'
                    f'<span>{key}</span>'
                    f'</div>'
                )
            else:
                html_parts.append(
                    f'<div class="tree-item {icon_class}" style="padding-left:{10 + indent*20}px">'
                    f'<span class="tree-icon">{icon}</span>'
                    f'<span>{key}/</span>'
                    f'</div>'
                )
                html_parts.append(render_tree(value, f"{path}{key}/", indent + 1))
        
        return '\n'.join(html_parts)
    
    total_files = len(code_artifacts)
    total_lines = sum(len(cf.get("content", "").split('\n')) for cf in code_artifacts.values())
    
    return f'''
    <div class="file-tree">
        <div class="tree-header">
            <span>📁 Project Files</span>
            <span style="margin-left:auto">{total_files} files, {total_lines} lines</span>
        </div>
        <script>
        function selectFile(filepath) {{
            window.parent.postMessage({{type: 'selectFile', filepath: filepath}}, '*');
        }}
        </script>
        {render_tree(tree)}
    </div>
    '''


def render_code_viewer(filepath: str, content: str, language: str = "python") -> str:
    """Render a code viewer with syntax highlighting."""
    highlighted = highlight_code(content, language)
    lang_display = language.upper()
    
    return f'''
    <div class="code-viewer">
        <div class="code-header">
            <span class="code-filename">📄 {filepath}</span>
            <span class="code-lang-badge">{lang_display}</span>
        </div>
        <div class="code-body">{highlighted}</div>
        <div class="file-stats">
            <span>📏 {len(content.split(chr(10)))} lines</span>
            <span>📦 {len(content)} bytes</span>
        </div>
    </div>
    '''


def _find_all_json_objects(text: str):
    """
    Find all JSON objects in text using brace counting.
    Returns list of (start, end, json_string) tuples.
    """
    results = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            # Count braces to find matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            json_start = i
            
            for j in range(i, len(text)):
                char = text[j]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if in_string:
                    continue
                    
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        results.append((json_start, j + 1, text[json_start:j+1]))
                        i = j + 1
                        break
        i += 1
    return results


def _extract_all_json_from_text(text: str):
    """
    Extract all JSON objects from text.
    Returns list of (prefix, json_string, suffix) tuples for each JSON found.
    """
    json_objects = _find_all_json_objects(text)
    if not json_objects:
        return None
    
    return json_objects


def _format_json_to_readable(parsed: dict, indent_level: int = 0) -> str:
    """Convert parsed JSON to readable text format that looks like human typing."""
    indent = "  " * indent_level
    
    if isinstance(parsed, dict):
        # Agent response with message + ideas
        if "message" in parsed and "ideas" in parsed:
            parts = []
            if parsed.get("message"):
                parts.append(parsed["message"])
            
            if parsed.get("ideas") and isinstance(parsed["ideas"], list):
                parts.append("")
                for i, idea in enumerate(parsed["ideas"], 1):
                    if isinstance(idea, dict):
                        title = idea.get("title", f"Idea {i}")
                        parts.append(f"{i}. {title}")
                        if idea.get("description"):
                            desc = idea['description'][:150]
                            if len(idea['description']) > 150:
                                desc += "..."
                            parts.append(f"   {desc}")
            
            if parsed.get("closing_message"):
                parts.append("")
                parts.append(parsed["closing_message"])
            
            return "\n".join(parts)
        
        # Agent response with message + evaluations
        if "message" in parsed and "evaluations" in parsed:
            parts = []
            if parsed.get("message"):
                parts.append(parsed["message"])
            
            if parsed.get("evaluations") and isinstance(parsed["evaluations"], list):
                parts.append("")
                for i, eval_item in enumerate(parsed["evaluations"], 1):
                    if isinstance(eval_item, dict):
                        title = eval_item.get("idea_title", f"Idea {i}")
                        score = eval_item.get("total_score", "?")
                        parts.append(f"{i}. {title} - {score}/10")
            
            if parsed.get("closing_message"):
                parts.append("")
                parts.append(parsed["closing_message"])
            
            return "\n".join(parts)
        
        # Agent response with message + rankings
        if "message" in parsed and "ranking" in parsed:
            parts = []
            if parsed.get("message"):
                parts.append(parsed["message"])
            
            if parsed.get("ranking") and isinstance(parsed["ranking"], list):
                parts.append("")
                parts.append("อันดับที่แนะนำ: " + ", ".join(str(r) for r in parsed["ranking"]))
            
            if parsed.get("closing_message"):
                parts.append("")
                parts.append(parsed["closing_message"])
            
            return "\n".join(parts)
        
        # Generic dict - just show string values
        lines = []
        for key, value in parsed.items():
            if isinstance(value, str):
                lines.append(f"{value}")
            elif isinstance(value, (int, float, bool)):
                lines.append(f"{value}")
        return "\n".join(lines) if lines else str(parsed)
    
    elif isinstance(parsed, list):
        lines = []
        for item in parsed:
            if isinstance(item, dict):
                lines.append(_format_json_to_readable(item, indent_level))
            else:
                lines.append(f"{indent}• {item}")
        return "\n".join(lines)
    
    return str(parsed)


def format_json_as_html(text: str) -> str:
    """Convert text to HTML, replacing all JSON objects with readable text."""
    import json
    try:
        # Find all JSON objects in the text
        json_objects = _extract_all_json_from_text(text)
        
        if not json_objects:
            # No JSON found, format as regular text
            return format_text_to_html(text)
        
        # Process text from end to start to maintain correct indices
        result = text
        for start, end, json_str in reversed(json_objects):
            try:
                parsed = json.loads(json_str)
                readable = _format_json_to_readable(parsed)
            except json.JSONDecodeError:
                readable = json_str
            
            # Replace the JSON string with readable text
            result = result[:start] + readable + result[end:]
        
        return format_text_to_html(result)
        
    except Exception:
        return format_text_to_html(text)


def format_text_to_html(text: str) -> str:
    """Convert plain text with markdown-like syntax to HTML."""
    import re
    import html
    
    # Escape HTML first
    text = html.escape(text)
    
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    
    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    
    # Code: `text`
    text = re.sub(r'`([^`]+)`', r'<code style="background:#2D2D2D;padding:2px 6px;border-radius:4px;font-size:0.85em">\1</code>', text)
    
    # Line breaks
    text = text.replace('\n', '<br>')
    
    return text


def render_bubbles(msgs):
    parts = []
    for m in msgs:
        et = m.get("event_type", "message")
        an = m.get("agent_name", "System")
        txt = m.get("message", "")
        ag = AGENTS.get(an, {"icon": "🤖", "color": "#999", "bg": "#F5F5F5"})
        ic, co, bg = ag["icon"], ag["color"], ag["bg"]
        if et in ("phase_start", "phase_complete"):
            parts.append(f'<div class="sys">{txt}</div>')
        elif et == "error":
            parts.append(f'<div class="sys" style="color:#D32F2F;background:#FFEBEE">{txt}</div>')
        elif et == "message":
            # Format the message content properly
            formatted_content = format_json_as_html(txt)
            parts.append(
                f'<div class="msg">'
                f'<div class="ava" style="background:{bg}">{ic}</div>'
                f'<div class="bub-body">'
                f'<div class="bub-name" style="color:{co}">{an}</div>'
                f'<div class="bub" style="background:{bg};white-space:normal">{formatted_content}</div>'
                f'<div class="bub-time">{ftime()}</div>'
                f'</div></div>'
            )
    return "\n".join(parts)


def main():
    st.set_page_config(page_title="Hackathon Copilot", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    if "eidx" not in st.session_state:
        st.session_state.eidx = 0
    if "started" not in st.session_state:
        st.session_state.started = False
    if "export_code_path" not in st.session_state:
        st.session_state.export_code_path = None
    if "export_pitch_path" not in st.session_state:
        st.session_state.export_pitch_path = None

    st.markdown(CSS, unsafe_allow_html=True)

    if not st.session_state.session_id:
        render_create()
        st.stop()
    else:
        render_chat()
        st.stop()


def render_create():
    st.markdown("""
    <div class="create-card">
        <div style="font-size:4rem;margin-bottom:0.5rem">🚀</div>
        <div style="font-size:2rem;font-weight:800;color:#FF6B00;margin-bottom:0.3rem">Hackathon Copilot</div>
        <div style="color:#999;font-size:1rem;margin-bottom:2rem">AI-Powered Multi-Agent Team for Hackathon Success</div>
    </div>
    """, unsafe_allow_html=True)

    theme = st.text_input("🎯 Hackathon Theme", placeholder="e.g., AI for Education", key="c_theme")
    const = st.text_area("📏 Constraints", value="48-hour hackathon, solo developer", key="c_const", height=80)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Session", type="primary", disabled=not theme, use_container_width=True):
            with st.spinner("Creating session..."):
                res = api("POST", "/sessions", {"theme": theme, "constraints": const})
            if res:
                st.session_state.session_id = res["session_id"]
                st.session_state.msgs = []
                st.session_state.eidx = 0
                st.session_state.started = False
                st.rerun()
            else:
                st.error("Cannot reach API server. Make sure it's running on port 8000.")


def render_chat():
    sid = st.session_state.session_id

    # Poll events
    try:
        r = requests.get(f"{API_BASE_URL}/sessions/{sid}/events", params={"since_index": st.session_state.eidx}, timeout=3)
        if r.status_code == 200:
            resp = r.json()
            new_events = resp.get("events", [])
            if new_events:
                for ev in new_events:
                    st.session_state.msgs.append(ev)
                    st.session_state.eidx = ev.get("index", 0) + 1
    except Exception:
        pass

    state = api("GET", f"/sessions/{sid}")
    if not state:
        st.error("Session not found"); return

    layer = state.get("current_layer", "")
    order = ["idle","ideation","judging","hitl_1","planning","architecting","building","critiquing","hitl_2","pitching","complete"]
    progress = 0
    try: progress = (order.index(layer)+1)/len(order)*100
    except: pass

    status = {
        "idle":"🟡 พร้อมแล้ว","ideation":"🧠 สุรเดชกำลัง brainstorming...","judging":"⚖️ วันเพ็ญกำลัง evaluating...",
        "hitl_1":"⏸️ เลือกไอเดีย","planning":"📋 สมศักดิ์กำลัง planning...","architecting":"🏗️ พิมพ์ใจกำลัง designing...",
        "building":"🔨 ธนภัทรกำลัง coding...","critiquing":"🔍 วิชัยกำลัง reviewing...","hitl_2":"⏸️ ตรวจสอบโค้ด",
        "pitching":"🎤 อรุณีกำลัง preparing...","complete":"✅ เสร็จสมบูรณ์!","error":"❌ เกิดข้อผิดพลาด",
    }.get(layer, layer)

    theme_val = state.get("theme") or "Hackathon"

    # Chat header
    st.markdown(f"""
    <div class="chat-container">
        <div class="chat-hdr">
            <div>
                <div style="font-weight:700;font-size:1rem">🚀 {theme_val}</div>
                <div style="font-size:0.75rem;opacity:0.85;margin-top:2px">{status}</div>
            </div>
            <div style="font-size:0.65rem;opacity:0.7">{sid[:8]}</div>
        </div>
        <div class="pbar-wrap">
            <div style="background:#E8E0D8;height:4px;">
                <div style="background:linear-gradient(90deg,#FF6B00,#FFB300);height:100%;width:{progress}%;transition:width 0.3s;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Messages
    if st.session_state.msgs:
        st.markdown(f'<div class="chat-container"><div class="msgs">{render_bubbles(st.session_state.msgs)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-container"><div style="text-align:center;padding:3rem;color:#CCC">⏳ กำลังรอการตอบสนองจาก AI...</div></div>', unsafe_allow_html=True)

    # Idea selection
    if layer == "hitl_1" and not state.get("selected_idea"):
        ideas = state.get("ideas", [])
        if ideas:
            has_wanphen = any(m.get("agent_name") == "วันเพ็ญ" for m in st.session_state.msgs)
            has_sudet_response = any(
                m.get("agent_name") == "สุรเดช" and ("ตอบกลับ" in m.get("message", "") or "ตอบกลับ" in m.get("message", ""))
                for m in st.session_state.msgs
            )
            
            if has_wanphen and has_sudet_response:
                st.markdown("### 🎯 เลือกไอเดียที่ต้องการ")
                st.caption("คลิกเลือกไอเดีย แล้ว AI จะเริ่มพัฒนาต่อ")
                cols = st.columns(min(len(ideas), 3))
                for i, idea in enumerate(ideas):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"### {idea.get('title','')}")
                            st.markdown(idea.get("description","")[:120] + "...")
                            st.markdown(f"** Tech:** {', '.join(idea.get('tech_stack',[]))}")
                            if st.button("📌 เลือกไอเดียนี้นะ", key=f"pi_{idea.get('id')}", use_container_width=True):
                                api("POST", f"/sessions/{sid}/select-idea", {"idea_id": idea.get("id")})
                                st.session_state.msgs.append({"event_type":"message","agent_name":"System","message":f"✅ เลือก: {idea.get('title','')}"})
                                st.rerun()
            else:
                st.markdown("""
                <div style="text-align:center;padding:1.5rem;background:white;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.05)">
                    <div style="font-size:2.5rem;margin-bottom:0.5rem">⚖️</div>
                    <div style="font-weight:700;color:#FF6B00;margin-bottom:0.25rem">กำลังรอความเห็นจากวันเพ็ญ...</div>
                    <div style="font-size:0.85rem;color:#999">วันเพ็ญกำลังวิเคราะห์และให้คะแนนไอเดียอยู่ โปรดรอซักครู่</div>
                </div>
                """, unsafe_allow_html=True)

    # Export section (when complete)
    if layer == "complete":
        st.markdown("---")
        st.markdown("### 📦 ดาวน์โหลดไฟล์")
        st.caption("ดาวน์โหลดโค้ดและไฟล์พิตชิ่งสำหรับนำเสนอ")
        
        # Export code
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📁 Export Code (ZIP)", type="primary", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์โค้ด..."):
                    res = api("GET", f"/sessions/{sid}/export/code")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        # Store filepath for download
                        st.session_state.export_code_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
        
        with c2:
            if st.button("📊 Export Pitch Materials (ZIP)", type="primary", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์พิตชิ่ง..."):
                    res = api("GET", f"/sessions/{sid}/export/pitch")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_pitch_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
        
        # Show download buttons if exports exist
        if hasattr(st.session_state, 'export_code_path') and st.session_state.export_code_path:
            with open(st.session_state.export_code_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Code ZIP",
                    data=f,
                    file_name=f"code_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
        
        if hasattr(st.session_state, 'export_pitch_path') and st.session_state.export_pitch_path:
            with open(st.session_state.export_pitch_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Pitch Materials ZIP",
                    data=f,
                    file_name=f"pitch_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

    # Code review with File Tree + Code Viewer
    if layer == "hitl_2":
        code_artifacts = state.get("code_artifacts", {})
        
        # Initialize selected file in session state
        if "selected_file" not in st.session_state:
            # Default to first file or README.md
            if code_artifacts:
                st.session_state.selected_file = "README.md" if "README.md" in code_artifacts else next(iter(code_artifacts.keys()))
            else:
                st.session_state.selected_file = None
        
        st.markdown("### 🔍 ตรวจสอบโค้ด")
        st.caption("คลิกที่ไฟล์ใน tree เพื่อดูโค้ด | โค้ดถูกสร้างเรียบร้อยแล้ว ต้องการอนุมัติหรือแก้ไข?")
        
        # Convert code_artifacts from dict to proper format for rendering
        code_dict = {}
        if code_artifacts:
            for fp, cf in code_artifacts.items():
                if isinstance(cf, dict):
                    code_dict[fp] = cf
                else:
                    code_dict[fp] = {
                        "filepath": cf.get("filepath", fp) if hasattr(cf, "get") else fp,
                        "content": cf.get("content", "") if hasattr(cf, "get") else str(cf),
                        "language": cf.get("language", "python") if hasattr(cf, "get") else get_language_from_path(fp),
                    }
        
        # Two-column layout for code review
        col_tree, col_code = st.columns([1, 2])
        
        with col_tree:
            # File Tree
            tree_html = build_file_tree(code_dict, st.session_state.selected_file)
            st.markdown(tree_html, unsafe_allow_html=True)
            
            # Create a selectbox for file selection (fallback for Streamlit)
            file_list = list(code_dict.keys()) if code_dict else []
            if file_list:
                selected = st.selectbox(
                    "📄 เลือกไฟล์:",
                    options=file_list,
                    index=file_list.index(st.session_state.selected_file) if st.session_state.selected_file in file_list else 0,
                    key="file_selector",
                )
                if selected != st.session_state.selected_file:
                    st.session_state.selected_file = selected
                    st.rerun()
        
        with col_code:
            # Code Viewer
            if st.session_state.selected_file and st.session_state.selected_file in code_dict:
                cf = code_dict[st.session_state.selected_file]
                filepath = st.session_state.selected_file
                content = cf.get("content", "") if isinstance(cf, dict) else ""
                language = cf.get("language", get_language_from_path(filepath)) if isinstance(cf, dict) else get_language_from_path(filepath)
                
                code_html = render_code_viewer(filepath, content, language)
                st.markdown(code_html, unsafe_allow_html=True)
                
                # Copy button
                if st.button("📋 คัดลอกโค้ด", key="copy_code_btn"):
                    st.code(content, language=language if language != "text" else None)
            else:
                st.markdown('<div style="text-align:center;color:#666;padding:3rem">👈 เลือกไฟล์เพื่อดูโค้ด</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Review actions
        st.markdown("### 📝 Review Actions")
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("✅ อนุมัติโค้ด", type="primary", use_container_width=True):
                api("POST", f"/sessions/{sid}/review-code", {"approved": True})
                st.rerun()
        with c2:
            fb = st.text_area("💬 Feedback (ถ้าต้องการแก้ไข)", key="rfb", height=50, placeholder="อธิบายสิ่งที่ต้องการให้แก้ไข...")
            if st.button("❌ ส่งกลับแก้ไข", use_container_width=True):
                api("POST", f"/sessions/{sid}/review-code", {"approved": False, "feedback": fb})
                st.rerun()

    # Bottom bar
    st.markdown('<div style="display:flex;gap:8px;padding:8px 0">', unsafe_allow_html=True)
    has_code = state.get("code_artifacts") or layer in ["hitl_2", "pitching", "complete"]
    has_pitch = state.get("narrative") or layer in ["pitching", "complete"]
    btn_count = 3 if (has_code and has_pitch) else (2 if (has_code or has_pitch) else 1)
    cols = st.columns([1, 1] + ([1] * btn_count))
    idx = 0
    with cols[idx]:
        idx += 1
        if st.button("🆕 New Session", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.msgs = []
            st.session_state.started = False
            st.session_state.export_code_path = None
            st.session_state.export_pitch_path = None
            st.rerun()
    with cols[idx]:
        idx += 1
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    if has_code:
        with cols[idx]:
            idx += 1
            if st.button("📁 Export Code", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์โค้ด..."):
                    res = api("GET", f"/sessions/{sid}/export/code")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_code_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
    if has_pitch:
        with cols[idx]:
            idx += 1
            if st.button("📊 Export Pitch", use_container_width=True):
                with st.spinner("กำลังเตรียมไฟล์พิตชิ่ง..."):
                    res = api("GET", f"/sessions/{sid}/export/pitch")
                    if res:
                        st.success(f"✅ สร้างไฟล์เรียบร้อย: `{res['filepath']}`")
                        st.info("💡 ไฟล์ถูกบันทึกในโฟลเดอร์ `data/exports/`")
                        st.session_state.export_pitch_path = res['filepath']
                    else:
                        st.error("❌ ไม่สามารถสร้างไฟล์ได้")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show download buttons if exports exist (always visible)
    if hasattr(st.session_state, 'export_code_path') and st.session_state.export_code_path:
        try:
            with open(st.session_state.export_code_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Code ZIP",
                    data=f,
                    file_name=f"code_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_code_btn",
                )
        except Exception:
            st.session_state.export_code_path = None
    
    if hasattr(st.session_state, 'export_pitch_path') and st.session_state.export_pitch_path:
        try:
            with open(st.session_state.export_pitch_path, "rb") as f:
                st.download_button(
                    label="⬇️ ดาวน์โหลด Pitch Materials ZIP",
                    data=f,
                    file_name=f"pitch_{sid}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_pitch_btn",
                )
        except Exception:
            st.session_state.export_pitch_path = None

    # Auto-start
    if not state.get("is_paused") and not st.session_state.started:
        st.session_state.started = True
        api("POST", f"/sessions/{sid}/start")

    # Auto-refresh: stop when paused, only refresh on new events when running
    is_paused = state.get("is_paused", False)
    prev_count = st.session_state.get("_prev_msg_count", 0)
    curr_count = len(st.session_state.msgs)
    st.session_state._prev_msg_count = curr_count
    
    if is_paused:
        pass
    elif st.session_state.started:
        if curr_count > prev_count:
            time.sleep(0.5)
            st.rerun()
        else:
            time.sleep(1.5)
            st.rerun()


if __name__ == "__main__":
    main()