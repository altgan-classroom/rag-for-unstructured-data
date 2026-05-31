import asyncio
import logging
import os
import sys
from typing import Dict, Any, Callable
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from core.retrieval_api.services.chat_service import ChatService
from core.retrieval_api.managers.storage_manager import LocalStorageManager
from core.retrieval_api.managers.llm_manager import LLMManager
from core.retrieval_api.managers.settings_manager import SettingsManager

from core.retrieval_api.models.base import ChatMessage, ChatHistory
from core.retrieval_api.schemas.api import ChatRequest, ChatResponse
from core.retrieval_api.schemas.rag import ChatRAGRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load test environment variables
load_dotenv(".env.test")

async def test_basic_chat():
    """Test basic chat functionality."""
    try:
        # Initialize settings manager
        settings_manager = SettingsManager()
        
        # Initialize managers
        storage_manager = LocalStorageManager(settings_manager.get_config)
        llm_manager = LLMManager(settings_manager)
        
        # Initialize chat service
        chat_service = ChatService(storage_manager, llm_manager, settings_manager)
        
        # Create test request
        request = ChatRequest(
            chat_id="test-chat-1",
            message="Hello, how are you?",
            metadata={"test": True}
        )
        
        # Process request
        response = await chat_service.process_chat(request)
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert response.chat_id == request.chat_id
        assert response.message is not None
        assert len(response.message) > 0
        assert response.metadata is not None
        assert "model" in response.metadata
        
        logger.info("Basic chat test passed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in basic chat test: {str(e)}")
        return False

async def test_rag_chat():
    """Test RAG-based chat functionality."""
    try:
        # Initialize settings manager
        settings_manager = SettingsManager()
        print("yes")
        # Initialize managers
        storage_manager = LocalStorageManager(settings_manager.get_config)
        llm_manager = LLMManager(settings_manager)
        print("llm model object", llm_manager._llm)
        # Initialize chat service
        chat_service = ChatService(storage_manager, llm_manager, settings_manager)
        
        # Create test request
        request = ChatRequest(
            chat_id="test-chat-2",
            message="give me wellbore geometry details of GM2?",
            metadata={"category": "oil_gas"}
        )
        
        # Process request
        response = await chat_service.process_rag_chat(request)

        
        # Verify response
        assert isinstance(response, StreamingResponse)
        assert response.chat_id == request.chat_id
        assert response.message is not None
        assert len(response.message) > 0
        assert response.metadata is not None
        assert "model" in response.metadata
        assert "sources" in response.metadata
        
        logger.info("RAG chat test passed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in RAG chat test: {str(e)}")
        return False

async def test_chat_history():
    """Test chat history functionality."""
    try:
        # Initialize settings manager
        settings_manager = SettingsManager()
        
        # Initialize managers
        storage_manager = LocalStorageManager(settings_manager.get_config)
        llm_manager = LLMManager(settings_manager)
        
        # Initialize chat service
        chat_service = ChatService(storage_manager, llm_manager, settings_manager)
        
        # Create test chat ID
        chat_id = "test-chat-3"
        
        # Send multiple messages
        messages = [
            "Hello, I have a question about climate change.",
            "What are the main causes?",
            "And what are the potential solutions?"
        ]
        
        for message in messages:
            request = ChatRequest(
                chat_id=chat_id,
                message=message,
                metadata={"test": True}
            )
            response = await chat_service.process_chat(request)
            assert response.chat_id == chat_id
            assert response.message is not None
        
        # Get chat history
        history = await chat_service.get_chat_history(chat_id)
        assert history is not None
        assert len(history.messages) == len(messages) * 2  # Each message has a user and assistant response
        
        logger.info("Chat history test passed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in chat history test: {str(e)}")
        return False

async def main():
    """Run all tests."""
    try:
        # Run tests
        basic_chat_result = await test_basic_chat()
        rag_chat_result = await test_rag_chat()
        history_result = await test_chat_history()
        
        # Print results
        logger.info("\nTest Results:")
        logger.info(f"Basic Chat: {'✓' if basic_chat_result else '✗'}")
        logger.info(f"RAG Chat: {'✓' if rag_chat_result else '✗'}")
        logger.info(f"Chat History: {'✓' if history_result else '✗'}")
        
    except Exception as e:
        logger.error(f"Error in main test execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 