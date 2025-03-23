"""
Ollama client functionality for the Jira MCP package
"""
import json
import hashlib
import time
import httpx
from ..utils.logging import logger
from ..config import config

# Simple memory cache for Ollama responses
ollama_cache = {}

def ask_ollama(prompt, system_message=None):
    """
    Send a prompt to Ollama and get a response.
    
    Args:
        prompt: The text prompt to send to Ollama
        system_message: Optional system message to provide context
        
    Returns:
        str: The response from Ollama
    """
    # Generate a cache key from the prompt and system message
    cache_key = hashlib.md5((prompt + (system_message or "")).encode()).hexdigest()
    
    # Check if we have a cached response and it's still valid
    if cache_key in ollama_cache:
        timestamp, cached_response = ollama_cache[cache_key]
        if time.time() - timestamp < config.ollama_cache_ttl:
            logger.info(f"Using cached Ollama response for prompt: {prompt[:50]}...")
            return cached_response
        else:
            # Expired, remove from cache
            del ollama_cache[cache_key]
            logger.debug(f"Removed expired cache entry for key: {cache_key}")
    
    try:
        # Create the request data
        data = {
            "model": config.ollama_model,
            "prompt": prompt,
            "system": system_message if system_message else "",
            "stream": False,  # We want a complete response, not streaming
            "raw": False,     # We want a processed response, not raw output
            "temperature": config.ollama_temperature,
            "context_length": config.ollama_context_length
        }
        
        logger.info(f"Sending prompt to Ollama: {prompt[:100]}...")
        
        # Make synchronous request to Ollama with timeout
        response = httpx.post(
            f"{config.ollama_base_url}/api/generate",
            json=data,
            timeout=config.ollama_timeout
        )
        
        # Log the raw response for debugging
        logger.debug(f"Raw Ollama response: {response.text[:500]}...")
        
        if response.status_code == 200:
            try:
                # Try to parse the response as JSON
                result = response.json()
                logger.info("Received response from Ollama")
                
                # Extract the actual response text from various Ollama response formats
                response_text = _extract_response_text(result)
                
                # Cache the response
                if len(ollama_cache) >= config.ollama_cache_size:
                    # Remove oldest entry if cache is full
                    oldest_key = min(ollama_cache.keys(), key=lambda k: ollama_cache[k][0])
                    del ollama_cache[oldest_key]
                    logger.debug(f"Removed oldest cache entry for key: {oldest_key}")
                
                ollama_cache[cache_key] = (time.time(), response_text)
                logger.debug(f"Added new cache entry for key: {cache_key}")
                
                return response_text
            except json.JSONDecodeError as je:
                logger.error(f"JSON parsing error: {str(je)}")
                # Try to salvage a response from the text
                return _handle_json_error(response.text)
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return f"Error from Ollama API: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error calling Ollama: {str(e)}")
        return f"Error calling Ollama: {str(e)}"

def _extract_response_text(result):
    """
    Extract the actual response text from various Ollama response formats
    
    Args:
        result: The parsed JSON response from Ollama
        
    Returns:
        str: The extracted response text
    """
    # Check for different response formats
    if isinstance(result, dict):
        # The /api/generate endpoint returns a response field
        if "response" in result:
            return result["response"]
        # Fallback to message format if using /api/chat
        elif "message" in result and isinstance(result["message"], dict):
            return result["message"].get("content", "No content in response")
        else:
            # Return the first string value we find
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 10:
                    return value
            
            # If we're here, we didn't find a good response format, log the full structure
            logger.warning(f"Unexpected Ollama response structure: {result}")
            return str(result)
    else:
        return str(result)

def _handle_json_error(raw_text):
    """
    Try to extract a meaningful response when JSON parsing fails
    
    Args:
        raw_text: The raw response text
        
    Returns:
        str: The extracted response or error message
    """
    # Try to extract just text content if there's JSON-like structure
    if len(raw_text) > 10:
        if '"content":' in raw_text:
            try:
                start_idx = raw_text.find('"content":') + 11
                end_idx = raw_text.find('",', start_idx)
                if end_idx > start_idx:
                    return raw_text[start_idx:end_idx]
            except:
                pass
        
        # Return the raw text if it's not too long
        if len(raw_text) < 5000:
            return f"Raw response (JSON parsing failed): {raw_text}"
    
    return "Error parsing Ollama response"

def is_ollama_available():
    """
    Check if Ollama is available and responding
    
    Returns:
        bool: True if Ollama is available, False otherwise
    """
    try:
        response = httpx.get(
            f"{config.ollama_base_url}/api/version",
            timeout=config.ollama_timeout
        )
        if response.status_code == 200:
            logger.info(f"Ollama is available at {config.ollama_base_url}")
            return True
        else:
            logger.warning(f"Ollama returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"Ollama is not available: {str(e)}")
        return False 