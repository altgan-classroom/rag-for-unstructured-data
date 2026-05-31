import os
import uuid
import warnings
from unittest.mock import MagicMock, patch

import pytest

from core.connectors.manager import ConnectorManager
from core.connectors.models import ConnectorConfig, ConnectorType, UserAccess
from core.ingest.markdown import (
    MarkDown,
    docling_extract,
    markitdown_extract,
    pymupdf4llm_extract,
)

# Add this at the top of your test file
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Real PDF URL for testing
REAL_PDF_URL = "https://orca-rag-documents.s3.ap-south-1.amazonaws.com/oil-and-gas/1211523415_20191113_CCS1_Well_Summary_Sheet.pdf"

# More comprehensive markdown sample
DUMMY_MARKDOWN = """# Test Document

## Introduction
This is a comprehensive test markdown document used for testing PDF extraction tools.

### Features
- Feature 1: Testing extraction capabilities
- Feature 2: Validating markdown formatting
- Feature 3: Ensuring proper content handling

## Technical Details
The document contains:
1. Headers and subheaders
2. Bullet points
3. Numbered lists
4. **Bold text** and *italic text*
5. [Hyperlinks](https://example.com)

### Code Example
```python
def sample_function():
    return "Hello, World!"
```

## Conclusion
This document serves as a test case for our PDF to markdown converters.
"""


@pytest.fixture
def mock_connector():
    """Fixture to create a mock connector."""
    connector = MagicMock()
    connector.download_file.return_value = f"/tmp/{uuid.uuid4()}.pdf"
    return connector


@pytest.fixture
def connector_manager():
    """Fixture to create a connector manager with test configuration."""
    manager = ConnectorManager()

    # Add test S3 configuration
    s3_config = ConnectorConfig(
        connector_type=ConnectorType.S3,
        company_id="test_company",
        config={
            "bucket": "",
            "aws_access_key_id": "",
            "aws_secret_access_key": "",
            "region": "ap-south-1",
        },
    )
    manager.add_company_connector(s3_config)

    # Add test user access
    user_access = UserAccess(
        user_id="test_user",
        company_id="test_company",
        connector_type=ConnectorType.S3,
        permissions={"read": True, "write": True},
    )
    manager.set_user_access(user_access)

    return manager


class TestMarkItDownExtract:
    """Test suite for MarkItDown extraction functionality."""

    @pytest.mark.integration
    def test_markitdown_extract_real_pdf(self, connector_manager):
        """Test markitdown_extract with a real PDF URL."""
        if os.environ.get("CI"):
            pytest.skip("Skipping integration test in CI environment")

        connector = connector_manager.get_connector(
            user_id="test_user",
            company_id="test_company",
            connector_type=ConnectorType.S3,
        )

        result = markitdown_extract(REAL_PDF_URL, connector)

        assert isinstance(result, MarkDown)
        assert result.content is not None
        assert len(result.content) > 0
        print(f"MarkItDown extracted {len(result.content)} characters")

    def test_markitdown_extract_mocked(self, mock_connector):
        """Test markitdown_extract with mocked PDF content."""
        with patch("markitdown.MarkItDown") as mock_markitdown:
            # Mock the MarkItDown instance and its convert method
            mock_markitdown_instance = MagicMock()
            mock_markitdown.return_value = mock_markitdown_instance

            # Create a mock result with our dummy markdown
            mock_result = MagicMock()
            mock_result.text_content = DUMMY_MARKDOWN
            mock_markitdown_instance.convert.return_value = mock_result

            # Call the function
            result = markitdown_extract("test.pdf", mock_connector)

            # Verify mock interactions
            mock_connector.connect.assert_called_once()
            mock_connector.download_file.assert_called_once_with("test.pdf")
            mock_markitdown_instance.convert.assert_called_once_with(
                mock_connector.download_file.return_value
            )

            # Check results
            assert result.content == DUMMY_MARKDOWN
            assert isinstance(result.metadata, dict)


class TestDoclingExtract:
    """Test suite for Docling extraction functionality."""

    @pytest.mark.integration
    def test_docling_extract_real_pdf(self, connector_manager):
        """Test docling_extract with a real PDF URL."""
        if os.environ.get("CI"):
            pytest.skip("Skipping integration test in CI environment")

        connector = connector_manager.get_connector(
            user_id="test_user",
            company_id="test_company",
            connector_type=ConnectorType.S3,
        )

        result = docling_extract(REAL_PDF_URL, connector)

        assert isinstance(result, MarkDown)
        assert result.content is not None
        assert len(result.content) > 0
        print(f"Docling extracted {len(result.content)} characters")

    def test_docling_extract_mocked(self, mock_connector):
        """Test docling_extract with mocked PDF content."""
        with patch(
            "docling.document_converter.DocumentConverter"
        ) as mock_document_converter:
            # Mock the DocumentConverter instance and its convert method
            mock_converter_instance = MagicMock()
            mock_document_converter.return_value = mock_converter_instance

            # Create a mock result with document that returns our dummy markdown
            mock_result = MagicMock()
            mock_document = MagicMock()
            mock_document.export_to_markdown.return_value = DUMMY_MARKDOWN
            mock_result.document = mock_document
            mock_converter_instance.convert.return_value = mock_result

            # Call the function
            result = docling_extract("test.pdf", mock_connector)

            # Verify mock interactions
            mock_connector.connect.assert_called_once()
            mock_connector.download_file.assert_called_once_with("test.pdf")
            mock_converter_instance.convert.assert_called_once_with(
                mock_connector.download_file.return_value
            )

            # Check results
            assert result.content == DUMMY_MARKDOWN
            assert isinstance(result.metadata, dict)


class TestPyMuPDF4LLMExtract:
    """Test suite for PyMuPDF4LLM extraction functionality."""

    @pytest.mark.integration
    def test_pymupdf4llm_extract_real_pdf(self, connector_manager):
        """Test pymupdf4llm_extract with a real PDF URL."""
        if os.environ.get("CI"):
            pytest.skip("Skipping integration test in CI environment")

        connector = connector_manager.get_connector(
            user_id="test_user",
            company_id="test_company",
            connector_type=ConnectorType.S3,
        )

        result = pymupdf4llm_extract(REAL_PDF_URL, connector)

        assert isinstance(result, MarkDown)
        assert result.content is not None
        assert len(result.content) > 0
        print(f"PyMuPDF4LLM extracted {len(result.content)} characters")

    def test_pymupdf4llm_extract_mocked(self, mock_connector):
        """Test pymupdf4llm_extract with mocked PDF content."""
        with patch("pymupdf4llm.to_markdown") as mock_to_markdown:
            mock_to_markdown.return_value = DUMMY_MARKDOWN

            # Call the function
            result = pymupdf4llm_extract("test.pdf", mock_connector)

            # Verify mock interactions
            mock_connector.connect.assert_called_once()
            mock_connector.download_file.assert_called_once_with("test.pdf")
            mock_to_markdown.assert_called_once_with(
                mock_connector.download_file.return_value
            )

            # Check results
            assert result.content == DUMMY_MARKDOWN
            assert isinstance(result.metadata, dict)
