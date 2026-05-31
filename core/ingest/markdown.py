import logging
import os
from typing import Any, Dict, List, Optional
import base64
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse

from pydantic import BaseModel

from core.connectors import BaseConnector
from .config import config

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Suppress PyMuPDF warnings about missing CropBox
logging.getLogger('fitz').setLevel(logging.ERROR)


class MarkDown(BaseModel):
    pages: List[str] # List of markdown pages
    metadata: Dict[str, Any]


def _get_file_with_connector(
    file_path: str,
    connector: BaseConnector,
) -> str:
    """Download file using the appropriate connector.

    Args:
        file_path: The path to the file in the storage system
        connector: Initialized connector instance

    Returns:
        Local path to the downloaded file
    """
    try:
        # If file_path is a URL, extract the bucket path
        if file_path.startswith(('http://', 'https://')):
            parsed_url = urlparse(file_path)
            bucket_path = parsed_url.path.lstrip('/')
        else:
            bucket_path = file_path

        connector.connect()
        local_path = connector.download_file(bucket_path)
        return local_path
    except Exception as e:
        raise Exception(f"Failed to download file using connector: {str(e)}") from e


def _process_image_with_llm(img, llm_client) -> str:
    """Process an image using the LLM client.
    
    Args:
        img: PIL Image object
        llm_client: Instance of LLMClient for making LLM requests
        
    Returns:
        str: Description of the image content from the LLM
    """
    try:
        from io import BytesIO
        import base64
        
        # Convert image to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Prepare the messages for the LLM
        messages = [
            {
                "role": "system",
                "content": """You are an advanced Optical Character Recognition (OCR) system. Your task is to accurately extract all textual content from the provided image. Format your response in clear, well-structured markdown. Your tasks include:

1. **Text Extraction**
   - Transcribe ALL visible text with perfect accuracy
   - Use `code blocks` for verbatim text when appropriate
   - Indicate any unclear text with [unclear: ...]

2. **Figures & Charts**
   - Describe data points, trends, and patterns
   - Note axes labels, units, and scales
   - Include legend information
   - Highlight any annotations or callouts
   - Use markdown tables for structured data when applicable

3. **Formatting Guidelines**
   - Use headers (#, ##) to organize sections
   - Use bullet points for lists
   - **Bold** important information
   - Use tables for tabular data
   - Include descriptive alt text for visual elements

Be thorough and precise, especially with technical or numerical data. Maintain the original context and relationships between different elements.
Do not include any additional text other than the markdown-formatted description of the content in image.
"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this image and provide a detailed markdown-formatted description including all visible text and visual elements. Structure your response with appropriate markdown formatting for better readability."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_str}",
                            "detail": "high"
                        },
                    },
                ]
            }
        ]
        
        # Get the response from the LLM using configured defaults
        response = llm_client.chat_complete(
            messages=messages,
            model=config.LLM_DEFAULT_MODEL,
            temperature=config.LLM_DEFAULT_TEMPERATURE
        )
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error processing image with LLM: {str(e)}")
        return f"*Could not process image with LLM: {str(e)}*"


def multimodal_extract(
    file_path: str,
    connector: BaseConnector,
    metadata: Dict[str, Any] = None,
    use_llm_for_images: bool = False,
    llm_client = None,
    **kwargs: Any,
) -> MarkDown:
    """Extract content from a PDF including text, tables, and images with OCR.

    Args:
        file_path: The path to the file in the storage system
        connector: Initialized connector instance
        metadata: Optional metadata to include with the markdown
        use_llm_for_images: Whether to use an LLM to describe images
        llm_client: Instance of LLMClient for making LLM requests
        **kwargs: Additional parameters (currently unused, for compatibility)

    Returns:
        MarkDown: Object containing the extracted content and metadata

    Raises:
        ImportError: If required libraries (pdfplumber, PyMuPDF, PIL, pytesseract) are not installed.
        Exception: For any errors during extraction
    """
    if metadata is None:
        metadata = {}

    # Check for required imports
    try:
        import pdfplumber
        import fitz  # PyMuPDF
        from PIL import Image
        import pytesseract
        import io
    except ImportError as e:
        raise ImportError(
            "Required libraries not found. Please install with: "
            "pip install pdfplumber pymupdf pillow pytesseract"
        ) from e

    temp_file_path = None
    markdown_pages = []
    img_metadata = {}

    try:
        # Get file using connector
        temp_file_path = _get_file_with_connector(file_path, connector)

        # Use pdfplumber for text and table extraction
        with pdfplumber.open(temp_file_path) as pdf:
            # Use fitz (PyMuPDF) for image extraction
            doc = fitz.open(temp_file_path)
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                fitz_page = doc.load_page(page_num)
                
                page_markdown = f"\n\n# Page {page_num + 1}\n\n"

                # --- Extract Text ---
                text = page.extract_text()
                if text:
                    page_markdown += text + "\n"

                # --- Extract Tables ---
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        page_markdown += "\n\n"
                        # Header row
                        header = table[0]
                        page_markdown += "| " + " | ".join(str(h) if h is not None else "" for h in header) + " |\n"
                        # Separator line
                        page_markdown += "|---" * len(header) + "|\n"
                        # Data rows
                        for row in table[1:]:
                            page_markdown += "| " + " | ".join(str(cell) if cell is not None else "" for cell in row) + " |\n"
                        page_markdown += "\n"

                # --- Extract Images and Perform OCR ---
                image_list = fitz_page.get_images(full=True)
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    try:
                        img = Image.open(io.BytesIO(image_bytes))

                        # Convert image to bytes
                        buffered = io.BytesIO()
                        img_format = image_ext.upper() if image_ext.upper() in ["JPEG", "PNG", "GIF"] else "PNG"
                        img.save(buffered, format=img_format)

                        if len(buffered.getvalue()) / 1024 < float(config.MIN_IMAGE_SIZE):
                            # These are probably logos and other small images that are not useful for OCR
                            continue
                        
                        # Generate a unique filename for the image
                        doc_name = os.path.splitext(os.path.basename(file_path))[0]
                        img_filename = f"{doc_name}_page{page_num+1}_img{img_index+1}.{img_format.lower()}"
                        img_key = f"page_{page_num+1}_image_{img_index+1}"
                        
                        try:
                            # Upload image directly to S3
                            img_path = f"images/{doc_name}/{img_filename}"
                            connector.upload_file(
                                io.BytesIO(buffered.getvalue()),
                                img_path
                            )
                            
                            # Get the URL for the image using connector method
                            img_url = connector.get_url(img_path)
                            
                            # Store image metadata with S3 URL
                            img_metadata[img_key] = {
                                "url": img_url,
                                "format": img_format.lower(),
                                "dimensions": f"{img.width}x{img.height}",
                                "size_kb": len(buffered.getvalue()) / 1024
                            }

                            # Add image reference to Markdown with a special format for later processing
                            page_markdown += f"\n![Image {img_index+1} on page {page_num+1}](image-ref:{img_key})\n"

                        except Exception as save_error:
                            logger.error(f"Failed to upload image {img_index+1} to S3: {str(save_error)}")
                            # Fallback to just storing metadata without the image URL
                            img_metadata[img_key] = {
                                "error": f"Failed to upload image: {str(save_error)}",
                                "format": img_format.lower(),
                                "dimensions": f"{img.width}x{img.height}",
                                "size_kb": len(buffered.getvalue()) / 1024
                            }

                    except Exception as img_e:
                        logger.error(f"Error processing image {img_index+1} on page {page_num+1}: {img_e}")
                        page_markdown += f"\n*Could not process image {img_index+1} on page {page_num+1}: {img_e}*\n"

                    # Process image with LLM if enabled
                    if use_llm_for_images and llm_client:
                        try:
                            llm_description = _process_image_with_llm(img, llm_client)
                            if llm_description:
                                page_markdown += f"\n**LLM Description of Image {img_index+1} on page {page_num+1}:**\n"
                                page_markdown += llm_description + "\n"
                        except Exception as llm_e:
                            logger.warning(f"Could not process image {img_index+1} with LLM: {llm_e}")
                            page_markdown += f"\n*Could not process image {img_index+1} with LLM: {llm_e}*\n"
                    else:
                        # Perform OCR on the image
                        try:
                            ocr_text = pytesseract.image_to_string(img)
                            if ocr_text.strip():
                                page_markdown += f"\n**OCR Text from Image {img_index+1} on page {page_num+1}:**\n"
                                page_markdown += ocr_text.strip() + "\n"
                        except Exception as ocr_e:
                            logger.warning(f"Could not perform OCR on image {img_index+1} on page {page_num+1}: {ocr_e}")
                            page_markdown += f"\n*Could not perform OCR on image {img_index+1} on page {page_num+1}: {ocr_e}*\n"

                page_markdown += "\n\n---\n\n"
                markdown_pages.append(page_markdown)


        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        metadata.update({"images": img_metadata})
        # print(markdown_pages)
        return MarkDown(pages=markdown_pages, metadata=metadata)

    except Exception as e:
        logger.error(f"Error extracting content from PDF: {str(e)}")
        raise Exception(f"Failed to extract content from PDF: {str(e)}") from e