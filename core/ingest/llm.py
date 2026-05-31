"""
Flexible LLM client that supports multiple LLM providers.

This module provides a unified interface to interact with different LLM providers
like OpenAI and OpenRouter.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from enum import Enum
import logging

from .config import config

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"

class MessageRole(Enum):
    """Message roles for chat completion."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message(Dict):
    """A message in the conversation."""
    def __init__(self, role: Union[MessageRole, str], content: str, **kwargs):
        if isinstance(role, MessageRole):
            role = role.value
        super().__init__(role=role, content=content, **kwargs)

class BaseLLMClient(ABC):
    """Base class for LLM clients."""
    
    @abstractmethod
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0-2), uses config default if None
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass

class OpenAIClient(BaseLLMClient):
    """Client for OpenAI's API."""
    
    def __init__(self, api_key: str, organization: Optional[str] = None):
        """Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key
            organization: Optional organization ID
        """
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, organization=organization)
        except ImportError:
            raise ImportError("Please install openai package: pip install openai")
    
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Get chat completion from the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to config.LLM_DEFAULT_MODEL)
            temperature: Sampling temperature (defaults to config.LLM_DEFAULT_TEMPERATURE)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the API
            
        Returns:
            Generated text response
        """
        response = self.client.chat.completions.create(
            model=model or config.LLM_DEFAULT_MODEL,
            messages=messages,
            temperature=temperature or config.LLM_DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

class OpenRouterClient(BaseLLMClient):
    """Client for OpenRouter's API."""
    
    def __init__(self, api_key: str, base_url: str = None):
        """Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            base_url: Base URL for the API (defaults to config value)
        """
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=base_url or config.OPENROUTER_BASE_URL,
                api_key=api_key
            )
        except ImportError:
            raise ImportError("Please install openai package: pip install openai")
    
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Get chat completion from the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to config.LLM_DEFAULT_MODEL)
            temperature: Sampling temperature (defaults to config.LLM_DEFAULT_TEMPERATURE)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the API
            
        Returns:
            Generated text response
        """
        response = self.client.chat.completions.create(
            model=model or config.LLM_DEFAULT_MODEL,
            messages=messages,
            temperature=temperature or config.LLM_DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

class LLMClient:
    """Unified client for different LLM providers."""
    
    def __init__(
        self,
        provider: Union[LLMProvider, str],
        api_key: str,
        **kwargs
    ):
        """Initialize the LLM client.
        
        Args:
            provider: LLM provider (as enum or string)
            api_key: API key for the provider
            **kwargs: Additional provider-specific parameters
        """
        if isinstance(provider, str):
            provider = LLMProvider(provider.lower())
        
        self.provider = provider
        
        if provider == LLMProvider.OPENAI:
            self.client = OpenAIClient(api_key=api_key, **kwargs)
        elif provider == LLMProvider.OPENROUTER:
            self.client = OpenRouterClient(api_key=api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in LLMProvider)}")
    
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier (uses config default if None)
            temperature: Sampling temperature (0-2, uses config default if None)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        return self.client.chat_complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

# Example usage:
"""
def example():
    # Initialize client
    client = LLMClient("openai", "your-api-key")
    
    # Chat completion example
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke"}
    ]
    
    response = client.chat_complete(
        messages=messages,
        model="gpt-4"
    )
    print(f"Response: {response}")

example()
"""