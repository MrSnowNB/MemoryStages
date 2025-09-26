# MemoryStages Architecture

This document outlines the architecture of MemoryStages, focusing on its core components and data flow.

## Stage 1 Implementation - SQLite Foundation Only

For this initial implementation, MemoryStages is built around a simple SQLite database with key-value storage capabilities and episodic event logging. This foundation provides:

- Key-value store functionality for persisting structured data
- Episodic memory through event logging
- A clean separation between the API layer and data access layer

## Core Components

### 1. Database Layer (`src/core/db.py`)
Handles database initialization, connection management, and health checks.

### 2. Data Access Object (`src/core/dao.py`)
Provides functions for interacting with the database including:
- Key-value operations (set, get, list, delete)
- Event logging (add and list events)

### 3. API Layer (`src/api/main.py`)
Serves as the HTTP interface to the system with endpoints for:
- Setting/getting key-value pairs
- Listing keys
- Deleting keys  
- Adding episodic events
- Getting event lists

### 4. Configuration (`src/core/config.py`)
Manages configuration variables including database path and debug settings.

## Vector Storage (Stage 2 - Coming Soon)

In Stage 2, we'll introduce vector storage capabilities to enable semantic search:

### Key Concepts
- **Vector Store Interface**: Abstract interface for storing and retrieving vectors  
- **Simple In-Memory Implementation**: Basic implementation using cosine similarity
- **Integration Points**: Seamless integration with existing key-value store

## Testing Strategy  

### Smoke Tests (`tests/test_smoke.py`)
End-to-end tests that verify the basic functionality of the system.

### Mock Vector Tests (`tests/test_vector_mock.py`)
Unit tests for the vector storage components to ensure proper implementation.
