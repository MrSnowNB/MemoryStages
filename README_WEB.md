# Memory Stages Web Chat Interface

A modern, responsive web interface for interacting with the Memory Stages multi-agent memory system.

## Overview

The web interface provides an intuitive chat experience where users can interact with the intelligent memory system powered by Ollama. The interface showcases the system's ability to use multiple AI agents working together with canonical SQLite memory and FAISS vector search.

## Features

- **Clean, Modern UI**: Responsive design that works on desktop and mobile
- **Real-time Chat**: Instant messaging interface with typing indicators
- **System Status**: Live health monitoring and agent status display
- **Memory Validation**: Visual indicators showing memory validation for responses
- **Confidence Scoring**: Real-time confidence levels and response metadata
- **Prompt Protection**: Client-side prompt injection protection
- **Session Management**: Automatic session handling for conversation continuity

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js/npm (optional, for advanced development)
- Ollama installed and running with models
- Memory Stages API server running

### Launch Both Services

```bash
# From project root directory

# Terminal 1: Start the API server
make dev

# Terminal 2: Start the web interface (opens browser automatically)
make web
```

Or launch both with the demo command (requires `screen` or `tmux`):

```bash
# Experimental: Launch both services
# Note: This may require additional setup for parallel execution
```

### Manual Setup

```bash
# 1. Start the API server (port 8000)
python -m uvicorn src.api.main:app --reload --host localhost --port 8000

# 2. Start the web server (port 3000)
python scripts/web_server.py
# Or use: make web
```

### Access the Interface

- **Web UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

## Configuration

### Environment Variables

The web interface automatically detects the API server location, but you can customize:

```bash
# In the web application, the API URL is configured at the top of the script tag:
const API_BASE_URL = window.location.origin; // Uses same host/port as web UI

# For custom API location, modify this variable in web/index.html
```

### Model Selection

Change the AI model by setting environment variables on the API server:

```bash
export OLLAMA_MODEL=liquid-rag:latest    # Default
export OLLAMA_MODEL=gemma:2b             # Alternative
export OLLAMA_MODEL=llama3.2:1b          # Lightweight
```

### Feature Flags

Enable different system features:

```bash
export CHAT_API_ENABLED=true     # Enable chat API
export SWARM_ENABLED=true        # Enable multi-agent swarm
export VECTOR_ENABLED=true       # Enable vector memory
export PRIVACY_ENFORCEMENT_ENABLED=true  # Enable privacy controls
```

## Usage Guide

### Basic Interaction

1. **Start the System**: Ensure both API and web servers are running
2. **Open the Interface**: Navigate to http://localhost:3000
3. **Check Status**: Verify the system shows "Healthy" in the status panel
4. **Start Chatting**: Type a message and press Enter or click Send

### Understanding Responses

The interface provides rich metadata for each response:

- **Confidence Level**: High/Medium/Low - How confident the AI is in the answer
- **Validation Status**: ✓ Memory Validated - Whether the response is backed by canonical memory
- **Agent Count**: How many agents contributed to the response
- **Processing Time**: How long the swarm took to generate the response

### Example Interactions

Try asking:

- "What is machine learning?"
- "Tell me about Python programming"
- "How does memory validation work?"
- "What programming languages do you know?"
- Questions about stored knowledge in your SQLite database

### Troubleshooting

#### System Not Responding
- **Check API Server**: Ensure `make dev` is running on port 8000
- **Check Web Server**: Ensure `make web` is running on port 3000
- **Check Ollama**: Ensure Ollama is running with required models
- **Check Browser Console**: Look for JavaScript errors

#### Responses Seem Inaccurate
- Check **confidence levels** - Low confidence may indicate unreliable responses
- **Memory validation** failures suggest the system doesn't have verified knowledge
- Try rephrasing questions or asking about topics in your stored knowledge base

#### Connection Errors
- Ensure both servers are running on the expected ports
- Check firewall settings if accessing from different machines
- Verify API_BASE_URL configuration in the web interface

## Development

### File Structure

```
web/
├── index.html          # Main chat interface
└── README.md          # This documentation
```

### Customization

The interface is built with vanilla HTML/CSS/JavaScript for maximum compatibility:

- **Styling**: Custom CSS with modern design patterns
- **JavaScript**: ES6+ features with fetch API for communication
- **Responsive**: Works on desktop, tablet, and mobile devices

### Advanced Development

For development with live reloading and modern tooling:

```bash
# Install Node.js dependencies (if available)
npm install --save-dev live-server

# Serve with live reloading
npx live-server web --port=3000 --open=/ --no-browser

# Modify index.html and changes will auto-refresh
```

## Architecture

### Communication Flow

```
User Request → Web UI → FastAPI (/chat/message) → Orchestrator → Agent Swarm → Memory Validation → Response → UI
```

### Components

- **Web UI**: Single-page chat interface with real-time updates
- **API Server**: FastAPI application serving REST endpoints
- **Orchestrator**: Rule-based coordinator managing multiple agents
- **Agent Swarm**: Multiple Ollama AI agents generating responses
- **Memory System**: SQLite canonical storage + FAISS vector search
- **Privacy Layer**: Access controls and audit logging

### Security Features

- **Prompt Injection Detection**: Both client and server-side protection
- **Input Validation**: Content length and format restrictions
- **Memory Isolation**: Agents cannot directly access sensitive data
- **Audit Logging**: All interactions are logged for security review
- **Session Management**: Proper session handling and cleanup

## System Requirements

### Minimum Hardware
- 4GB RAM (8GB recommended for multi-agent operation)
- Multi-core CPU (4+ cores recommended)
- 10GB free disk space for models and databases

### Software Dependencies
- Python 3.10+
- Ollama with supported models
- SQLite 3
- FAISS library for vector operations

### Browser Support
- Modern browsers with ES6+ support
- Fallback warning for outdated browsers
- Mobile-friendly responsive design

## Performance

The system is optimized for local operation:

- **Response Time**: Typically 1-3 seconds per response
- **Memory Usage**: ~2-4GB depending on model size
- **Concurrent Users**: Designed for single user, low concurrency
- **Offline Operation**: Fully local, no internet dependency

## Troubleshooting

### Common Issues

**"Failed to send message" Error**
```
Cause: API server not running or connection issue
Solution: Verify make dev is running and accessible
```

**"System Unhealthy" Status**
```
Cause: Ollama not running or model not available
Solution: Check `ollama list` and `ollama serve` status
```

**Low Confidence Responses**
```
Cause: Limited stored knowledge or query mismatch
Solution: Add more knowledge to the system or rephrase question
```

### Logs and Debugging

Enable debug mode for detailed logging:

```bash
export DEBUG=true
# Restart both servers
```

Check logs in:
- API server terminal output
- Browser developer console (F12)
- Ollama logs with `ollama logs`

## Contributing

The web interface follows the project's staged development approach. New features should be added through the established lockdown and testing process.

For UI improvements:
1. Follow existing code patterns
2. Test across different browsers and devices
3. Ensure accessibility compliance
4. Add documentation for new features

---

**Ready to chat with your memory system! 🤖💬**
