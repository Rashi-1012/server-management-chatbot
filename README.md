# Chennai Server Management Chatbot

A comprehensive server management dashboard and AI chatbot built with FastAPI, Streamlit, and SQLAlchemy. This application provides real-time monitoring, management, and intelligent querying of server infrastructure for a Chennai data center.

## 🚀 Features

### 📊 Dashboard & Monitoring
- **Real-time Server Dashboard** - Interactive web interface with charts and metrics
- **Server Status Monitoring** - Track server uptime, status, and performance
- **Environment Management** - Organize servers by Development, Production, and Staging
- **Visual Analytics** - Charts showing server distribution, status, and resource utilization

### 🤖 AI Chatbot
- **Natural Language Queries** - Ask questions about your servers in plain English
- **Intelligent Responses** - Get detailed information about server status, configurations, and metrics
- **Contextual Understanding** - The AI understands server management terminology and context

### 🛠️ Server Management
- **Complete Server Inventory** - Track all server details including IP, OS, resources, and ownership
- **User Management** - Manage users and access logs
- **RESTful API** - Complete REST API for programmatic access
- **Database Integration** - SQLite database with SQLAlchemy ORM

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │     FastAPI     │    │    SQLite       │
│   Frontend      │───▶│     Backend     │───▶│    Database     │
│   (Port 8501)   │    │   (Port 8000)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                                               │
        ▼                                               ▼
┌─────────────────┐                            ┌─────────────────┐
│   AI Chatbot    │                            │   Server Data   │
│   Integration   │                            │   & Analytics   │
└─────────────────┘                            └─────────────────┘
```

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package installer)

## 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/server-management-chatbot.git
   cd server-management-chatbot
   ```

2. **Install dependencies:**
   ```bash
   # If you encounter SSL certificate issues, use this command:
   python -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
   
   # Or the standard command if SSL works:
   pip install -r requirements.txt
   ```

3. **Set up environment variables (optional):**
   A `.env` file has been created for you. Edit it to add your API keys:
   ```bash
   # Edit the .env file and replace the placeholder values:
   
   # For OpenAI GPT models (recommended):
   OPENAI_API_KEY=sk-your-actual-openai-api-key-here
   
   # Alternative: For Google Gemini models:
   GEMINI_API_KEY=your-actual-gemini-api-key-here
   
   # Get OpenAI API key from: https://platform.openai.com/api-keys
   # Get Gemini API key from: https://aistudio.google.com/app/apikey
   ```

## 🚀 Usage

### Running the Application

1. **Start the FastAPI backend:**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`

2. **Start the Streamlit frontend:**
   ```bash
   streamlit run app.py
   ```
   The dashboard will be available at `http://localhost:8501`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Key API Endpoints

- `GET /api/summary` - Get server summary statistics
- `GET /api/servers` - List all servers
- `GET /api/servers/{server_id}` - Get specific server details
- `GET /api/users` - List all users

## 💬 Chatbot Usage

The AI chatbot can answer various questions about your server infrastructure:

- **"How many servers do we have?"**
- **"Which servers are down?"**
- **"Show me production servers"**
- **"What's the status of chennai-web-01?"**
- **"List servers by environment"**

## 📁 Project Structure

```
server-management-chatbot/
├── app.py              # Streamlit frontend application
├── main.py             # FastAPI backend application
├── chatbot.py          # AI chatbot logic and integration
├── database.py         # Database configuration and setup
├── models.py           # SQLAlchemy database models
├── requirements.txt    # Python dependencies
├── server_inventory.db # SQLite database (created automatically)
├── README.md          # This file
└── .gitignore         # Git ignore rules
```

## 🗄️ Database Schema

### Servers Table
- **id**: Unique identifier
- **name**: Server name
- **ip_address**: Server IP address
- **fqdn**: Fully qualified domain name
- **os**: Operating system
- **environment**: dev/staging/production
- **status**: up/down/maintenance
- **resources**: CPU, memory, disk specifications
- **owner**: Assigned user
- **tags**: Metadata tags

### Users Table
- **id**: Unique identifier
- **name**: User full name
- **email**: User email address
- **role**: User role/position
- **department**: User department

### Access Logs Table
- **id**: Unique identifier
- **user_id**: Foreign key to users
- **server_id**: Foreign key to servers
- **action**: Action performed
- **timestamp**: When action occurred

## 🤖 AI Integration

The chatbot uses OpenAI's GPT models for natural language processing. To enable AI features:

1. Get an OpenAI API key from https://platform.openai.com/
2. Set the `OPENAI_API_KEY` environment variable
3. Restart the application
4. you can use other models as well.
Without the API key, the chatbot will use rule-based responses.

## 🔒 Security Considerations

- Database is stored locally (SQLite)
- No authentication implemented (suitable for internal use)
- API keys should be stored in environment variables
- Consider adding authentication for production use

## 🐛 Troubleshooting

### Common Issues

1. **SSL Certificate Errors during pip install**:
   ```bash
   # Use trusted hosts to bypass SSL verification
   python -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
   
   # For individual packages:
   python -m pip install package_name --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
   ```

2. **Port already in use**: 
   - Change ports in `main.py` and `app.py`
   - Kill existing processes using the ports

3. **Database connection errors**:
   - Ensure write permissions in the project directory
   - Check if `server_inventory.db` exists

4. **Package import errors**:
   - Verify all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version compatibility

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, please create an issue in the GitHub repository or contact the development team.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Frontend powered by [Streamlit](https://streamlit.io/)
- Database managed with [SQLAlchemy](https://www.sqlalchemy.org/)
- AI capabilities provided by [OpenAI](https://openai.com/)

---

**Server Management Made Simple** 🖥️✨

## Features

 **Server Inventory Management**
- Complete CMDB with server details, specifications, and ownership
- Real-time status monitoring
- Environment-based organization (production, staging, development)

 **AI-Powered Chatbot**
- Natural language queries about server status
- Intelligent search and filtering
- Context-aware responses

 **Interactive Dashboard**
- Real-time metrics and visualizations
- Server status distribution
- Resource utilization analytics
- Activity monitoring

 **Advanced Analytics**
- Resource distribution analysis
- Environment vs status correlations
- Performance recommendations

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (easily replaceable with PostgreSQL)
- **Frontend**: Streamlit with Plotly visualizations
- **AI**: OpenAI GPT integration (optional)
- **Sample Data**: Pre-populated Chennai server inventory

## Quick Start

### 1. Install Dependencies

`ash
pip install -r requirements.txt
`

### 2. Setup Environment

Edit the `.env` file and add your API keys:
```
DATABASE_URL=sqlite:///./server_inventory.db

# For enhanced AI responses, add one of these:
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
# OR
GEMINI_API_KEY=your-actual-gemini-api-key-here

SECRET_KEY=your_secret_key_here
DEBUG=True
```

### 3. Initialize Database

`ash
python database.py
`

### 4. Start API Server

`ash
python main.py
`
API will be available at: http://localhost:8000

### 5. Start Web Application

`ash
python -m streamlit run app.py
`
Web app will be available at: http://localhost:8501

## Sample Data

The system comes pre-loaded with:
- 1 main Chennai hypervisor server
- 10 virtual machines (web, database, API, cache, etc.)
- 5 sample users with different roles
- Sample access logs and activity history

### Sample Servers:
- chennai-main-01 - Main hypervisor
- chennai-web-01 - Production web server
- chennai-db-01 - Production database
- chennai-api-01 - API gateway
- chennai-cache-01 - Redis cache server
- And more...

### Sample Users:
- Rajesh Kumar (Admin, DevOps)
- Priya Sharma (User, Development)
- Arjun Patel (User, QA)
- Meera Singh (User, Development)
- Karthik Reddy (Admin, Infrastructure)

## API Endpoints

### Server Management
- GET /api/servers - List all servers with filtering
- GET /api/servers/{id} - Get server by ID
- GET /api/servers/name/{name} - Get server by name
- GET /api/summary - Get server statistics
- GET /api/users - List all users

### Query Parameters
- environment - Filter by environment (production, staging, development)
- status - Filter by status (up, down, maintenance)
- location - Filter by location
- search - Search in name, IP, or notes

## Chatbot Queries

Try these natural language queries:

**Status Queries:**
- "How many servers do we have?"
- "Which servers are down?"
- "Show me servers that are up"
- "List servers in maintenance"

**Environment Queries:**
- "Show me production servers"
- "List development environment"
- "What staging servers do we have?"

**Specific Server Queries:**
- "What's the status of chennai-web-01?"
- "Show me details for the database server"
- "Find servers with 'api' in the name"

**Search Queries:**
- "Find Ubuntu servers"
- "Show me servers owned by Rajesh"
- "List servers with more than 8GB RAM"

## Web Interface

### Dashboard
- Server count metrics
- Status distribution charts
- Environment breakdown
- Recent activity log

### Server List
- Filterable server inventory
- Detailed server information
- Search functionality
- Export capabilities

### Chat Assistant
- Natural language interface
- Suggested questions
- Chat history
- Real-time responses

### Analytics
- Resource utilization charts
- OS distribution analysis
- Environment vs status heatmaps
- Automated recommendations

## Customization

### Adding Your Own Servers

Edit database.py and modify the seed_sample_data() function to add your actual server inventory.

### Integrating with Existing CMDB

Replace the SQLite database with your existing CMDB by:
1. Updating the database connection in database.py
2. Modifying the models in models.py to match your schema
3. Updating the API endpoints in main.py

### Adding Actions

To evolve from read-only to actionable:
1. Add action endpoints in main.py
2. Implement approval workflows
3. Add security and audit logging
4. Update the chatbot to handle action requests

## Security Considerations

 **This is a development/demo version**

For production use:
- Add authentication and authorization
- Implement proper secrets management
- Add input validation and sanitization
- Set up audit logging
- Use HTTPS and secure connections
- Implement rate limiting
- Add approval workflows for actions

## Troubleshooting

### Common Issues:

1. **API Connection Error**
   - Ensure the FastAPI server is running on port 8000
   - Check if there are any port conflicts

2. **Database Issues**
   - Run python database.py to reinitialize
   - Check file permissions for SQLite database

3. **Missing Dependencies**
   - Run pip install -r requirements.txt
   - Ensure Python 3.8+ is being used

4. **OpenAI API Issues**
   - The chatbot works without OpenAI (rule-based responses)
   - Add your API key to .env for enhanced responses

## Future Enhancements

 **Planned Features:**
- Slack/Teams integration
- Real-time server monitoring
- Automated health checks
- Action approval workflows
- Mobile app interface
- Integration with cloud providers
- Advanced alerting system

## Support

For questions or issues:
1. Check the troubleshooting section
2. Review the sample queries and API documentation
3. Test with the provided sample data first

---

**Built with Python, FastAPI, Streamlit, and AI** 
