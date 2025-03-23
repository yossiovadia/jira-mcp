"""
Ollama client module for the Jira MCP
"""
from .client import ask_ollama, is_ollama_available

# Re-export for simpler imports
__all__ = ['ask_ollama', 'is_ollama_available'] 