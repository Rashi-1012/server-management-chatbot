import openai
import requests
import json
import re
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

load_dotenv()

class ServerChatbot:
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            openai.api_key = self.openai_api_key
        
        # System prompt for the chatbot
        self.system_prompt = '''You are a helpful server management assistant for a Chennai data center. 
        You have access to live server data through API calls and can answer questions about:
        - Server status, specifications, and details
        - Who owns/manages servers
        - Server environments (production, staging, development)
        - Server locations and configurations
        
        Always provide accurate, up-to-date information from the live API. If you cannot find specific information,
        say so clearly. Be concise but helpful in your responses.
        
        When users ask about servers, always check the live data rather than relying on general knowledge.
        '''
    
    def call_api(self, endpoint: str, params: Dict = None) -> Dict:
        """Call the server management API"""
        try:
            url = f"{self.api_base_url}{endpoint}"
            response = requests.get(url, params=params or {}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API call failed: {str(e)}"}
    
    def get_server_summary(self) -> Dict:
        """Get server summary statistics"""
        return self.call_api("/api/summary")
    
    def search_servers(self, query: str) -> List[Dict]:
        """Search for servers by name, IP, or notes"""
        return self.call_api("/api/servers", {"search": query})
    
    def get_servers_by_environment(self, environment: str) -> List[Dict]:
        """Get servers by environment"""
        return self.call_api("/api/servers", {"environment": environment})
    
    def get_servers_by_status(self, status: str) -> List[Dict]:
        """Get servers by status"""
        return self.call_api("/api/servers", {"status": status})
    
    def get_server_by_name(self, name: str) -> Dict:
        """Get specific server by name"""
        return self.call_api(f"/api/servers/name/{name}")
    
    def get_all_servers(self) -> List[Dict]:
        """Get all servers"""
        return self.call_api("/api/servers")
    
    def analyze_query(self, user_query: str) -> Dict[str, Any]:
        """Analyze user query to determine what data to fetch"""
        query_lower = user_query.lower()
        
        # Keywords for different types of queries
        status_keywords = ['up', 'down', 'running', 'offline', 'maintenance', 'status']
        environment_keywords = ['production', 'prod', 'staging', 'development', 'dev', 'test']
        summary_keywords = ['how many', 'total', 'count', 'summary', 'overview']
        search_keywords = ['find', 'search', 'show me', 'list']
        
        result = {
            'type': 'general',
            'data': {},
            'needs_api': True
        }
        
        # Check for summary requests
        if any(keyword in query_lower for keyword in summary_keywords):
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
        
        # Default to search
        else:
            result['type'] = 'search'
            result['data'] = self.search_servers(user_query)
        
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
    
    def generate_response(self, user_query: str) -> str:
        """Generate a response to user query"""
        # Analyze the query and get relevant data
        analysis = self.analyze_query(user_query)
        
        # Handle different types of responses
        if analysis['type'] == 'summary':
            data = analysis['data']
            if 'error' in data:
                return f"Sorry, I couldn't get the server summary: {data['error']}"
            
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
            
            return response
        
        elif analysis['type'] == 'status_query':
            servers = analysis['data']
            if isinstance(servers, dict) and 'error' in servers:
                return f"Sorry, I couldn't get the server status: {servers['error']}"
            
            if not servers:
                return "No servers found matching that status."
            
            response = f"Found {len(servers)} servers:\n\n"
            for server in servers[:10]:  # Limit to first 10
                response += self.format_server_info(server) + "\n"
            
            if len(servers) > 10:
                response += f"\n... and {len(servers) - 10} more servers."
            
            return response
        
        elif analysis['type'] == 'specific_server':
            server = analysis['data']
            if isinstance(server, dict) and 'error' in server:
                return f"Sorry, I couldn't find that server: {server['error']}"
            
            return self.format_server_info(server)
        
        elif analysis['type'] in ['search', 'environment_query']:
            servers = analysis['data']
            if isinstance(servers, dict) and 'error' in servers:
                return f"Sorry, I couldn't search for servers: {servers['error']}"
            
            if not servers:
                return "No servers found matching your query."
            
            response = f"Found {len(servers)} servers:\n\n"
            for server in servers[:5]:  # Limit to first 5 for readability
                response += self.format_server_info(server) + "\n"
            
            if len(servers) > 5:
                response += f"\n... and {len(servers) - 5} more servers."
            
            return response
        
        # If we have OpenAI API key, use it for more natural responses
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            try:
                # Prepare context with the data
                context = f"User query: {user_query}\n\nRelevant server data: {json.dumps(analysis['data'], indent=2)}"
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            except Exception as e:
                # Fallback to rule-based response
                pass
        
        # Fallback response
        return "I have the server data but need more context to provide a helpful answer. Could you be more specific about what you'd like to know?"

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
