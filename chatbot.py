import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import google.generativeai as genai
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ServerChatbotError(Exception):
    """Base exception for ServerChatbot errors."""
    pass


class APIError(ServerChatbotError):
    """Exception raised for API-related errors."""
    pass


class GeminiError(ServerChatbotError):
    """Exception raised for Gemini-related errors."""
    pass


@dataclass
class CacheConfig:
    """Configuration for caching behavior."""
    ttl_seconds: int = 60
    max_api_cache_size: int = 50
    max_gemini_cache_size: int = 100


@dataclass
class PerformanceStats:
    """Performance statistics tracking."""
    api_calls: int = 0
    total_api_time: float = 0.0
    gemini_calls: int = 0
    total_gemini_time: float = 0.0
    gemini_errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def avg_api_time(self) -> float:
        """Average API response time."""
        return self.total_api_time / max(self.api_calls, 1)

    @property
    def avg_gemini_time(self) -> float:
        """Average Gemini response time."""
        return self.total_gemini_time / max(self.gemini_calls, 1)

    @property
    def cache_hit_ratio(self) -> float:
        """Cache hit ratio as percentage."""
        total_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / max(total_requests, 1)) * 100


    


class LoggerManager:
    """Centralized logging configuration."""
    
    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """Set up a logger with consistent formatting."""
        logger = logging.getLogger(name)
        
        if not logger.handlers:  # Avoid duplicate handlers
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(level)
        
        return logger


# Initialize logger
logger = LoggerManager.setup_logger(__name__)

class ServerChatbot:

    # Class constants
    DEFAULT_API_BASE_URL = "http://localhost:8000"
    DEFAULT_TIMEOUT = 10
    MAX_RETRIES = 3
    
    # Query classification keywords
    STATUS_KEYWORDS = frozenset([
        'up', 'down', 'running', 'offline', 'maintenance', 'status'
    ])
    
    ENVIRONMENT_KEYWORDS = frozenset([
        'production', 'prod', 'staging', 'development', 'dev', 'test'
    ])
    
    SUMMARY_KEYWORDS = frozenset([
        'how many', 'total', 'count', 'summary', 'overview'
    ])
    
    CONVERSATIONAL_KEYWORDS = frozenset([
        'explain', 'tell me about', 'describe', 'what do you think', 'analyze',
        'recommend', 'suggest', 'advice', 'opinion', 'insight', 'interpretation',
        'simple terms', 'in summary', 'overall', 'situation', 'health',
        'assessment', 'evaluation', 'report', 'brief', 'rundown', 'breakdown'
    ])
    
    def __init__(
        self,
        api_base_url: str = None,
        cache_config: CacheConfig = None,
        timeout: int = None
    ):
        
        self.api_base_url = api_base_url or self.DEFAULT_API_BASE_URL
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.cache_config = cache_config or CacheConfig()
        
        # Initialize caching
        self._api_cache: Dict[str, Any] = {}
        self._gemini_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Performance tracking
        self.stats = PerformanceStats()
        
        # Gemini client
        self._gemini_model: Optional[genai.GenerativeModel] = None
        
        # System prompt for Gemini
        self._system_prompt = self._build_system_prompt()
        
        logger.info(f"Initializing ServerChatbot with API: {self.api_base_url}")
        self._initialize_gemini()
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt for Gemini interactions."""
        return """You are a helpful server management assistant for a Chennai data center.
        
You have access to live server data and can answer questions about:
- Server status, specifications, and details
- Server ownership and management
- Server environments (production, staging, development)
- Server locations and configurations

Guidelines:
- Always provide accurate, up-to-date information from live data
- Be concise but comprehensive in responses
- Use proper formatting with line breaks and structure
- If information is unavailable, state this clearly
- Focus on actionable insights when possible
"""
    
    def _initialize_gemini(self) -> None:
        """Initialize Gemini client with proper error handling."""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key.startswith("your_"):
            logger.warning("No valid Gemini API key found. Operating in basic mode.")
            return
            
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            
            # Get model name from environment or use default
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            
            # Initialize the model
            self._gemini_model = genai.GenerativeModel(model_name)
            
            # Test the connection
            self._test_gemini_connection()
            logger.info(f"Gemini client initialized successfully with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise GeminiError(f"Gemini initialization failed: {e}")
    
    def _test_gemini_connection(self) -> None:
        """Test Gemini connection with a minimal API call."""
        if not self._gemini_model:
            return
            
        try:
            response = self._gemini_model.generate_content("Hello")
            logger.debug(f"Gemini connection test successful: {response.text[:50]}...")
        except Exception as e:
            logger.warning(f"Gemini connection test failed: {e}")
    
    @property
    def is_gemini_available(self) -> bool:
        """Check if Gemini client is available."""
        return self._gemini_model is not None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid based on TTL."""
        if cache_key not in self._cache_timestamps:
            return False
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self.cache_config.ttl_seconds
    
    def _get_from_api_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from API cache if valid."""
        if self._is_cache_valid(cache_key) and cache_key in self._api_cache:
            self.stats.cache_hits += 1
            logger.debug(f"API cache hit: {cache_key}")
            return self._api_cache[cache_key]
        
        self.stats.cache_misses += 1
        return None
    
    def _set_api_cache(self, cache_key: str, data: Any) -> None:
        """Store data in API cache with size management."""
        self._api_cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        
        # Manage cache size
        if len(self._api_cache) > self.cache_config.max_api_cache_size:
            self._cleanup_api_cache()
        
        logger.debug(f"API cache set: {cache_key}")
    
    def _get_from_gemini_cache(self, cache_key: str) -> Optional[str]:
        """Retrieve response from Gemini cache if valid."""
        if self._is_cache_valid(cache_key) and cache_key in self._gemini_cache:
            self.stats.cache_hits += 1
            logger.debug(f"Gemini cache hit: {cache_key}")
            return self._gemini_cache[cache_key]
        
        self.stats.cache_misses += 1
        return None
    
    def _set_gemini_cache(self, cache_key: str, response: str) -> None:
        """Store response in Gemini cache with size management."""
        self._gemini_cache[cache_key] = response
        self._cache_timestamps[cache_key] = time.time()
        
        # Manage cache size
        if len(self._gemini_cache) > self.cache_config.max_gemini_cache_size:
            self._cleanup_gemini_cache()
        
        logger.debug(f"Gemini cache set: {cache_key}")
    
    def _cleanup_api_cache(self) -> None:
        """Remove oldest entries from API cache."""
        sorted_keys = sorted(
            self._api_cache.keys(),
            key=lambda k: self._cache_timestamps.get(k, 0)
        )
        
        keys_to_remove = sorted_keys[:len(sorted_keys) // 4]  # Remove 25% oldest
        for key in keys_to_remove:
            self._api_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        
        logger.debug(f"API cache cleaned: removed {len(keys_to_remove)} entries")
    
    def _cleanup_gemini_cache(self) -> None:
        """Remove oldest entries from Gemini cache."""
        sorted_keys = sorted(
            self._gemini_cache.keys(),
            key=lambda k: self._cache_timestamps.get(k, 0)
        )
        
        keys_to_remove = sorted_keys[:len(sorted_keys) // 4]  # Remove 25% oldest
        for key in keys_to_remove:
            self._gemini_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        
        logger.debug(f"Gemini cache cleaned: removed {len(keys_to_remove)} entries")
    
    def call_api(self, endpoint: str, params: Dict = None) -> Dict:
       
        try:
            return self._make_api_request(endpoint, params)
        except APIError as e:
            return {"error": str(e)}
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        
        # Input validation
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
        
        # Create cache key
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        
        # Check cache first
        cached_data = self._get_from_api_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Prepare request
        url = urljoin(self.api_base_url, endpoint)
        start_time = time.time()
        
        logger.debug(f"Making API request: {url} with params: {params}")
        
        try:
            response = requests.get(
                url,
                params=params or {},
                timeout=self.timeout,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise APIError(f"Invalid JSON response from {endpoint}: {e}")
            
            # Update performance stats
            duration = time.time() - start_time
            self.stats.api_calls += 1
            self.stats.total_api_time += duration
            
            logger.info(
                f"API call to {endpoint} completed in {duration:.2f}s. "
                f"Response size: {len(str(data))} chars"
            )
            
            # Cache the response
            self._set_api_cache(cache_key, data)
            return data
            
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            error_msg = f"API timeout after {duration:.2f}s for {endpoint}"
            logger.error(error_msg)
            raise APIError(error_msg)
            
        except requests.exceptions.ConnectionError:
            duration = time.time() - start_time
            error_msg = f"Connection error after {duration:.2f}s for {endpoint}"
            logger.error(error_msg)
            raise APIError(error_msg)
            
        except requests.exceptions.HTTPError as e:
            duration = time.time() - start_time
            error_msg = f"HTTP error {e.response.status_code} after {duration:.2f}s for {endpoint}"
            logger.error(error_msg)
            raise APIError(error_msg)
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error after {duration:.2f}s for {endpoint}: {e}"
            logger.error(error_msg)
            raise APIError(error_msg)
    
    # API convenience methods with proper typing
    def get_server_summary(self) -> Dict[str, Any]:
        """Get comprehensive server summary statistics."""
        try:
            return self._make_api_request("/api/summary")
        except APIError as e:
            logger.error(f"Failed to get server summary: {e}")
            return {"error": str(e)}
    
    def search_servers(self, query: str) -> List[Dict[str, Any]]:
        """Search for servers by name, IP, or notes."""
        if not query.strip():
            return []
        
        try:
            result = self._make_api_request("/api/servers", {"search": query})
            return result if isinstance(result, list) else []
        except APIError as e:
            logger.error(f"Failed to search servers: {e}")
            return []
    
    def get_servers_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        """Get servers filtered by environment."""
        if not environment.strip():
            return []
        
        try:
            result = self._make_api_request("/api/servers", {"environment": environment})
            return result if isinstance(result, list) else []
        except APIError as e:
            logger.error(f"Failed to get servers by environment: {e}")
            return []
    
    def get_servers_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get servers filtered by status."""
        if not status.strip():
            return []
        
        try:
            result = self._make_api_request("/api/servers", {"status": status})
            return result if isinstance(result, list) else []
        except APIError as e:
            logger.error(f"Failed to get servers by status: {e}")
            return []
    
    def get_server_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific server by name."""
        if not name.strip():
            return None
        
        try:
            result = self._make_api_request(f"/api/servers/name/{name}")
            return result if isinstance(result, dict) and "error" not in result else None
        except APIError as e:
            logger.error(f"Failed to get server by name: {e}")
            return None
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get all servers with error handling."""
        try:
            result = self._make_api_request("/api/servers")
            return result if isinstance(result, list) else []
        except APIError as e:
            logger.error(f"Failed to get all servers: {e}")
            return []
    
    def analyze_query(self, user_query: str) -> Dict[str, Any]:
        """Analyze user query to determine what data to fetch"""
        query_lower = user_query.lower()

        # Keywords for different types of queries (reuse class-level sets for consistency)
        status_keywords = list(self.STATUS_KEYWORDS)
        environment_keywords = list(self.ENVIRONMENT_KEYWORDS)
        summary_keywords = list(self.SUMMARY_KEYWORDS)
        search_keywords = ['find', 'search', 'show me', 'list']
        conversational_keywords = list(self.CONVERSATIONAL_KEYWORDS)

        result = {
            'type': 'general',
            'data': {},
            'needs_api': True
        }
        
        # Check for conversational/explanatory queries first
        if any(keyword in query_lower for keyword in conversational_keywords):
            result['type'] = 'conversational'
            # Get summary data to provide context to the LLM
            result['data'] = self.get_server_summary()
            return result
        
        # Check for summary requests
        elif any(keyword in query_lower for keyword in summary_keywords):
            result['type'] = 'summary'
            result['data'] = self.get_server_summary()
        
        # Check for status queries
        elif any(keyword in query_lower for keyword in status_keywords):
            if 'down' in query_lower or 'offline' in query_lower:
                result['type'] = 'status_query'
                result['data'] = self.get_servers_by_status('down')
            elif 'up' in query_lower or 'running' in query_lower:
                result['type'] = 'status_query'
                result['data'] = self.get_servers_by_status('up')
            elif 'maintenance' in query_lower:
                result['type'] = 'status_query'
                result['data'] = self.get_servers_by_status('maintenance')
            else:
                result['type'] = 'all_servers'
                result['data'] = self.get_all_servers()
        
        # Check for environment queries
        elif any(keyword in query_lower for keyword in environment_keywords):
            for env in ['production', 'staging', 'development']:
                if env in query_lower or env[:4] in query_lower:
                    result['type'] = 'environment_query'
                    result['data'] = self.get_servers_by_environment(env)
                    break
        
        # Check for specific server queries
        elif 'chennai-' in query_lower or any(keyword in query_lower for keyword in ['web', 'db', 'api', 'cache']):
            # Extract potential server names
            server_patterns = [
                r'chennai-[\w-]+',
                r'web-?\d*',
                r'db-?\d*',
                r'api-?\d*',
                r'cache-?\d*'
            ]
            
            for pattern in server_patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    server_name = matches[0]
                    result['type'] = 'specific_server'
                    result['data'] = self.get_server_by_name(server_name)
                    break
            
            if result['type'] != 'specific_server':
                # If no specific server found, search
                result['type'] = 'search'
                result['data'] = self.search_servers(user_query)
        
        # Default to conversational with summary data for complex queries
        else:
            result['type'] = 'conversational'
            result['data'] = self.get_server_summary()
        
        return result
    
    def format_server_info(self, server: Dict) -> str:
        """Format server information for display"""
        if 'error' in server:
            return f"Error: {server['error']}"
        
        info = f"**{server['name']}**\n"
        info += f" IP: {server['ip_address']}\n"
        info += f" Status: {server['status'].upper()}\n"
        info += f" Environment: {server['environment']}\n"
        info += f" OS: {server['os']} {server.get('os_version', '')}\n"
        info += f" Resources: {server.get('cpu_cores', 'N/A')} cores, {server.get('memory_gb', 'N/A')}GB RAM\n"
        if server.get('owner_name'):
            info += f" Owner: {server['owner_name']}\n"
        if server.get('last_seen'):
            info += f" Last seen: {server['last_seen']}\n"
        
        return info
    
    def format_server_name_only(self, server: Dict) -> str:
        """Format server name only for simple lists"""
        if 'error' in server:
            return f"Error: {server['error']}"
        return f"{server['name']}"
    
    def _wants_names_only(self, user_query: str) -> bool:
        """Check if user wants only server names in response"""
        query_lower = user_query.lower()
        keywords = [
            'only', 'just', 'names only', 'only names', 'just names',
            'list names', 'server names', 'name only', 'only the names',
            'just the names', 'names of', 'which servers', 'what servers'
        ]
        
        # Check if query contains "only" or "just" with "names"
        if ('only' in query_lower and 'name' in query_lower) or \
           ('just' in query_lower and 'name' in query_lower) or \
           any(keyword in query_lower for keyword in keywords):
            return True
        
        # Check for patterns like "which servers are down" (implies names only)
        if query_lower.startswith(('which ', 'what ')) and 'server' in query_lower:
            return True
            
        return False
    
    # Removed deprecated OpenAI test method
    
    def generate_response(self, user_query: str) -> str:
        """Generate a response to user query with comprehensive logging."""
        start_time = time.time()
        logger.info(f"Processing user query: '{user_query[:100]}{'...' if len(user_query) > 100 else ''}'")
        
        try:
            # Analyze the query and get relevant data
            analysis = self.analyze_query(user_query)
            logger.debug(f"Query analysis result: type='{analysis['type']}'")
            
            # Handle different types of responses
            if analysis['type'] == 'summary':
                data = analysis['data']
                if 'error' in data:
                    logger.warning(f"Error getting server summary: {data['error']}")
                    return f"Sorry, I couldn't get the server summary: {data['error']}"
                
                logger.info("Generating server summary response")
                response = f"**Server Summary for Chennai Data Center:**\n\n"
                response += f" Total servers: {data['total_servers']}\n"
                response += f" Active servers: {data['active_servers']}\n"
                response += f" Servers up: {data['servers_up']}\n"
                response += f" Servers down: {data['servers_down']}\n"
                response += f" Servers in maintenance: {data['servers_maintenance']}\n\n"
                
                if data['environments']:
                    response += "**By Environment:**\n"
                    for env, count in data['environments'].items():
                        response += f" {env.title()}: {count} servers\n"
                
                duration = time.time() - start_time
                logger.info(f"Generated summary response in {duration:.2f}s")
                return response
            
            elif analysis['type'] == 'status_query':
                servers = analysis['data']
                if isinstance(servers, dict) and 'error' in servers:
                    logger.warning(f"Error getting server status: {servers['error']}")
                    return f"Sorry, I couldn't get the server status: {servers['error']}"
                
                if not servers:
                    return "No servers found matching that status."
                
                # Check if user wants only names
                names_only = self._wants_names_only(user_query)
                logger.info(f"Generating status query response for {len(servers)} servers (names_only={names_only})")
                
                if names_only:
                    # Minimal output: just names, one per line
                    response = "\n".join(self.format_server_name_only(s) for s in servers)
                else:
                    response = f"Found {len(servers)} servers:\n\n"
                    for server in servers[:10]:  # Limit to first 10 for detailed view
                        response += self.format_server_info(server) + "\n"
                    
                    if len(servers) > 10:
                        response += f"\n... and {len(servers) - 10} more servers."
                
                duration = time.time() - start_time
                logger.info(f"Generated status response in {duration:.2f}s")
                return response
            
            elif analysis['type'] == 'specific_server':
                server = analysis['data']
                if isinstance(server, dict) and 'error' in server:
                    logger.warning(f"Error finding specific server: {server['error']}")
                    return f"Sorry, I couldn't find that server: {server['error']}"
                
                logger.info("Generating specific server response")
                duration = time.time() - start_time
                logger.info(f"Generated specific server response in {duration:.2f}s")
                return self.format_server_info(server)
            
            elif analysis['type'] in ['search', 'environment_query']:
                servers = analysis['data']
                if isinstance(servers, dict) and 'error' in servers:
                    logger.warning(f"Error searching servers: {servers['error']}")
                    return f"Sorry, I couldn't search for servers: {servers['error']}"
                
                if not servers:
                    return "No servers found matching your query."
                
                # Check if user wants only names
                names_only = self._wants_names_only(user_query)
                logger.info(f"Generating search response for {len(servers)} servers (names_only={names_only})")
                
                if names_only:
                    # Minimal output: just names, one per line
                    response = "\n".join(self.format_server_name_only(s) for s in servers)
                else:
                    response = f"Found {len(servers)} servers:\n\n"
                    for server in servers[:5]:  # Limit to first 5 for readability
                        response += self.format_server_info(server) + "\n"
                    
                    if len(servers) > 5:
                        response += f"\n... and {len(servers) - 5} more servers."
                
                duration = time.time() - start_time
                logger.info(f"Generated search response in {duration:.2f}s")
                return response
            
            elif analysis['type'] == 'conversational':
                # For conversational queries, always use Gemini with context
                logger.info("Processing conversational query with Gemini")
                duration = time.time() - start_time
                logger.info(f"Routing to Gemini after {duration:.2f}s")
                return self._generate_gemini_response(user_query, analysis)
            
            # Try Gemini for more natural responses
            duration = time.time() - start_time
            logger.info(f"Fallback to Gemini after {duration:.2f}s")
            return self._generate_gemini_response(user_query, analysis)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error generating response after {duration:.2f}s: {e}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    def _generate_gemini_response(self, user_query: str, analysis: dict) -> str:
        """Generate response using Gemini with comprehensive error handling and caching."""
        cache_key = hashlib.md5(user_query.encode()).hexdigest()
        
        # Check cache first
        cached_response = self._get_from_gemini_cache(cache_key)
        if cached_response:
            age = time.time() - self._cache_timestamps.get(cache_key, 0)
            logger.info(f"Using cached Gemini response (age: {age:.1f}s)")
            return cached_response
        
        start_time = time.time()
        logger.info("Generating Gemini response")
        
        try:
            # Build context from analysis
            context = self._build_context_from_analysis(analysis)
            
            prompt = f"""{self._system_prompt}

Context about the servers:
{context}

User query: {user_query}

Please provide a helpful response based on the available server data. Keep it concise and informative."""

            logger.debug(f"Gemini prompt length: {len(prompt)} characters")
            
            if not self._gemini_model:
                logger.warning("Gemini model not available, using fallback response")
                return self._fallback_response(analysis)
            
            response = self._gemini_model.generate_content(prompt)
            
            if not response.text:
                logger.warning("Empty response from Gemini")
                return self._fallback_response(analysis)
            
            ai_response = response.text.strip()
            
            # Cache the response
            self._set_gemini_cache(cache_key, ai_response)
            
            duration = time.time() - start_time
            logger.info(f"Generated Gemini response in {duration:.2f}s")
            self.stats.gemini_calls += 1
            self.stats.total_gemini_time += duration
            
            return ai_response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Gemini API error after {duration:.2f}s: {e}")
            self.stats.gemini_errors += 1
            
            # Fallback response
            if analysis.get('data'):
                return "I found some relevant server information, but I'm having trouble generating a detailed response right now. Please try a more specific query."
            else:
                return "I'm having trouble accessing the Gemini service right now. Please try again later or rephrase your question."
    
    def _build_context_from_analysis(self, analysis: dict) -> str:
        """Build context string from analysis data."""
        context = ""
        
        if analysis['type'] == 'summary' and isinstance(analysis['data'], dict):
            data = analysis['data']
            context = f"Total servers: {data.get('total_servers', 'N/A')}, "
            context += f"Active: {data.get('active_servers', 'N/A')}, "
            context += f"Up: {data.get('servers_up', 'N/A')}, "
            context += f"Down: {data.get('servers_down', 'N/A')}"
            
        elif analysis.get('data') and isinstance(analysis['data'], list):
            servers = analysis['data'][:3]  # Limit context size
            context = f"Found {len(analysis['data'])} servers. Sample: "
            for server in servers:
                if isinstance(server, dict):
                    context += f"{server.get('hostname', 'Unknown')} ({server.get('status', 'Unknown')}), "
                    
        return context.strip(', ')
    
    # Consolidated performance and cache management (Gemini only)
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics (API + Gemini)."""
        return {
            "api_calls": self.stats.api_calls,
            "total_api_time": round(self.stats.total_api_time, 2),
            "avg_api_time": round(self.stats.avg_api_time, 2),
            "gemini_calls": self.stats.gemini_calls,
            "total_gemini_time": round(self.stats.total_gemini_time, 2),
            "avg_gemini_time": round(self.stats.avg_gemini_time, 2),
            "gemini_errors": self.stats.gemini_errors,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "cache_hit_ratio": round(self.stats.cache_hit_ratio, 1),
            "api_cache_size": len(self._api_cache),
            "gemini_cache_size": len(self._gemini_cache),
        }
    
    def _fallback_response(self, analysis: dict) -> str:
        """Generate fallback response when OpenAI is not available."""
        data = analysis.get('data', {})
        
        if analysis['type'] == 'summary' and isinstance(data, dict):
            response = "**Server Summary for Chennai Data Center:**\n\n"
            response += f"Total servers: {data.get('total_servers', 'N/A')}\n"
            response += f"Active servers: {data.get('active_servers', 'N/A')}\n"
            response += f"Servers up: {data.get('servers_up', 'N/A')}\n"
            response += f"Servers down: {data.get('servers_down', 'N/A')}\n"
            response += f"Servers in maintenance: {data.get('servers_maintenance', 'N/A')}\n"
            return response
        elif analysis['type'] in ['status_query', 'search', 'environment_query'] and isinstance(data, list):
            if data:
                response = f"Found {len(data)} servers:\n\n"
                for server in data[:3]:  # Show first 3
                    if isinstance(server, dict):
                        response += self.format_server_info(server) + "\n"
                if len(data) > 3:
                    response += f"\n... and {len(data) - 3} more servers."
                return response
            else:
                return "No servers found matching your criteria."
        elif analysis['type'] == 'specific_server' and isinstance(data, dict):
            return self.format_server_info(data)
        
        return "I have the server data but need more context to provide a helpful answer. Could you be more specific about what you'd like to know?"
    
    # Utility and management methods
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        api_valid = sum(1 for key in self._api_cache.keys() if self._is_cache_valid(key))
        gemini_valid = sum(1 for key in self._gemini_cache.keys() if self._is_cache_valid(key))
        
        return {
            "api_cache": {
                "total_entries": len(self._api_cache),
                "valid_entries": api_valid,
                "expired_entries": len(self._api_cache) - api_valid,
                "max_size": self.cache_config.max_api_cache_size
            },
            "gemini_cache": {
                "total_entries": len(self._gemini_cache),
                "valid_entries": gemini_valid,
                "expired_entries": len(self._gemini_cache) - gemini_valid,
                "max_size": self.cache_config.max_gemini_cache_size
            },
            "ttl_seconds": self.cache_config.ttl_seconds
        }
    
    def clear_cache(self, cache_type: str = "all") -> None:
        """
        Clear cached data.
        
        Args:
            cache_type: Type of cache to clear ("api", "gemini", or "all")
        """
        if cache_type in ("api", "all"):
            api_size = len(self._api_cache)
            self._api_cache.clear()
            logger.info(f"API cache cleared: {api_size} entries removed")
        
        if cache_type in ("gemini", "all"):
            gemini_size = len(self._gemini_cache)
            self._gemini_cache.clear()
            logger.info(f"Gemini cache cleared: {gemini_size} entries removed")
        
        if cache_type == "all":
            self._cache_timestamps.clear()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        health_status = {
            "api_connectivity": False,
            "gemini_availability": self.is_gemini_available,
            "cache_status": "healthy",
            "performance": self.get_performance_stats(),
            "timestamp": time.time()
        }
        
        try:
            # Test API connectivity
            summary = self.get_server_summary()
            health_status["api_connectivity"] = "error" not in summary
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            health_status["api_connectivity"] = False
        
        # Check cache health
        total_cache_size = len(self._api_cache) + len(self._gemini_cache)
        max_total_size = (
            self.cache_config.max_api_cache_size + 
            self.cache_config.max_gemini_cache_size
        )
        
        if total_cache_size > max_total_size * 0.9:
            health_status["cache_status"] = "warning"
        
        return health_status
    
    def __repr__(self) -> str:
        """String representation of the chatbot."""
        return (
            f"ServerChatbot(api_url='{self.api_base_url}', "
            f"gemini_available={self.is_gemini_available}, "
            f"api_calls={self.stats.api_calls})"
        )
    
# Example usage
if __name__ == "__main__":
    chatbot = ServerChatbot()
    
    # Test queries
    test_queries = [
        "How many servers do we have?",
        "Which servers are down?",
        "Show me production servers",
        "What's the status of chennai-web-01?",
        "List all servers"
    ]
    
    for query in test_queries:
        print(f"Q: {query}")
        print(f"A: {chatbot.generate_response(query)}")
        print("-" * 50)
