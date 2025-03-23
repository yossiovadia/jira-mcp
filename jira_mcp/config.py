"""
Configuration module for the Jira MCP package
"""
import os
from dotenv import load_dotenv
from .utils.logging import logger

class Config:
    """Configuration class for Jira MCP"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Script directory (used as default location for attachments)
        self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Attachments directory
        self.attachments_base_dir = os.getenv('MCP_ATTACHMENTS_PATH', 
                                             os.path.join(self.script_dir, "attachments"))
        # Ensure it exists
        os.makedirs(self.attachments_base_dir, exist_ok=True)
        
        # PDF support
        self.pdf_support = self._check_pdf_support()
        
        # Jira configuration
        self._load_jira_config()
        
        # Ollama configuration
        self._load_ollama_config()
        
        # Log configuration summary
        self._log_config_summary()
    
    def _check_pdf_support(self):
        """Check if PDF libraries are available"""
        try:
            import PyPDF2
            return True
        except ImportError:
            return False
    
    def _load_jira_config(self):
        """Load Jira configuration from environment variables"""
        # Primary Jira
        self.primary_jira_host = os.getenv('PRIMARY_JIRA_HOST')
        self.primary_jira_pat = os.getenv('PRIMARY_JIRA_PAT')
        self.primary_jira_username = os.getenv('PRIMARY_JIRA_USERNAME')
        self.primary_jira_password = os.getenv('PRIMARY_JIRA_PASSWORD')
        
        # Secondary Jira
        self.secondary_jira_host = os.getenv('SECONDARY_JIRA_HOST')
        self.secondary_jira_pat = os.getenv('SECONDARY_JIRA_PAT')
        
        # Backward compatibility - Nokia Jira
        self.nokia_jira_host = os.getenv('NOKIA_JIRA_HOST', self.primary_jira_host)
        self.nokia_jira_pat = os.getenv('NOKIA_JIRA_PAT', self.primary_jira_pat)
        self.nokia_jira_username = os.getenv('NOKIA_JIRA_USERNAME', self.primary_jira_username)
        self.nokia_jira_password = os.getenv('NOKIA_JIRA_PASSWORD', self.primary_jira_password)
        
        # Backward compatibility - Red Hat Jira
        self.redhat_jira_host = os.getenv('REDHAT_JIRA_HOST', self.secondary_jira_host)
        self.redhat_jira_pat = os.getenv('REDHAT_JIRA_PAT', self.secondary_jira_pat)
        
        # Legacy configuration (for backward compatibility)
        self.jira_host = os.getenv('JIRA_HOST', self.primary_jira_host)
        self.jira_pat = os.getenv('JIRA_PAT', self.primary_jira_pat)
        self.jira_username = os.getenv('JIRA_USERNAME', self.primary_jira_username)
        self.jira_password = os.getenv('JIRA_PASSWORD', self.primary_jira_password)
        
        # Project prefixes for Secondary Jira (for determining which Jira to use)
        self.secondary_project_prefixes = os.getenv('SECONDARY_PROJECT_PREFIXES', 'CNV').split(',')
        
        # Backward compatibility
        self.redhat_project_prefixes = os.getenv('REDHAT_PROJECT_PREFIXES', 
                                               self.secondary_project_prefixes)
        if isinstance(self.redhat_project_prefixes, str):
            self.redhat_project_prefixes = self.redhat_project_prefixes.split(',')
    
    def _load_ollama_config(self):
        """Load Ollama configuration from environment variables"""
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11435')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'deepseek-r1:14b-qwen-distill-q8_0')
        self.ollama_temperature = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
        self.ollama_context_length = int(os.getenv('OLLAMA_CONTEXT_LENGTH', '32768'))
        self.ollama_timeout = float(os.getenv('OLLAMA_TIMEOUT', '120.0'))
        self.ollama_cache_size = int(os.getenv('OLLAMA_CACHE_SIZE', '50'))
        self.ollama_cache_ttl = int(os.getenv('OLLAMA_CACHE_TTL', '3600'))
    
    def _log_config_summary(self):
        """Log configuration summary"""
        logger.info(f"Attachments directory set to: {self.attachments_base_dir}")
        logger.info(f"PDF support: {'Available' if self.pdf_support else 'Not available'}")
        
        # Log Jira configuration
        logger.info(f"Primary Jira host: {self.primary_jira_host or 'Not configured'}")
        logger.info(f"Secondary Jira host: {self.secondary_jira_host or 'Not configured'}")
        
        # Log Ollama configuration
        logger.info(f"Ollama URL: {self.ollama_base_url}")
        logger.info(f"Ollama model: {self.ollama_model}")
        logger.info(f"Ollama parameters: temperature={self.ollama_temperature}, "
                   f"context_length={self.ollama_context_length}, "
                   f"timeout={self.ollama_timeout}s")
        logger.info(f"Ollama cache: size={self.ollama_cache_size}, "
                   f"TTL={self.ollama_cache_ttl}s")

# Global configuration instance
config = Config() 