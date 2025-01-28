import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re
import logging
import tempfile
import os
import pymupdf4llm

# Setup logging
logger = logging.getLogger(__name__)

def setup_logging(debug=False):
    """Configure logging level and format"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def clean_wikipedia_content(html_content):
    """
    Clean Wikipedia HTML content by removing unnecessary elements
    """
    logger.debug("Starting Wikipedia content cleaning")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    unwanted_elements = [
        '.mw-editsection',  # Edit links
        '#mw-navigation',   # Navigation
        '#mw-head',         # Header
        '#mw-panel',        # Left sidebar
        '#footer',          # Footer
        '.reference',       # Reference numbers
        '.references',      # Reference section
        '.reflist',         # Reference list
        '.navbox',         # Navigation boxes at bottom
        '.thumb',          # Thumbnail images
        '.infobox',        # Infoboxes
        '.mbox-small',     # Small message boxes
        '#coordinates',     # Geo coordinates
        '.ambox',          # Article message boxes
        '.sistersitebox',  # Sister project links
    ]
    
    for selector in unwanted_elements:
        elements = soup.select(selector)
        logger.debug(f"Removing {len(elements)} elements matching '{selector}'")
        for element in elements:
            element.decompose()
    
    # Get main content
    content = soup.find(id='mw-content-text')
    if not content:
        logger.warning("No main content found in Wikipedia page")
        return None
    
    logger.debug("Successfully cleaned Wikipedia content")
    return str(content)

def html_to_markdown(html_content):
    """Convert HTML to Markdown with specific options"""
    logger.debug("Converting HTML to markdown")
    markdown = md(html_content, 
                 heading_style="ATX",      # Use # style headers
                 bullets="-",              # Use - for unordered lists
                 strip=['img', 'script'],  # Remove images and scripts
                 code_language='python')   # Default code language
    logger.debug(f"Converted markdown length: {len(markdown)} chars")
    return markdown

def clean_markdown(markdown_text):
    """Clean up markdown content"""
    if not markdown_text:
        logger.debug("Empty markdown text received")
        return ""
    
    logger.debug("Starting markdown cleanup")
    original_length = len(markdown_text)
    
    # Remove multiple blank lines
    markdown_text = re.sub(r'\n\s*\n', '\n\n', markdown_text)
    
    # Remove references
    markdown_text = re.sub(r'\[\d+\]', '', markdown_text)
    
    # Remove edit links
    markdown_text = re.sub(r'\[edit\]', '', markdown_text)
    
    # Remove remaining brackets
    markdown_text = re.sub(r'\[\]', '', markdown_text)
    
    cleaned_text = markdown_text.strip()
    logger.debug(f"Markdown cleanup complete. Length reduced from {original_length} to {len(cleaned_text)} chars")
    return cleaned_text

def fetch_and_parse_pdf(url):
    """
    Fetch and parse PDF content to markdown
    Returns None if failed
    """
    logger.debug(f"Fetching PDF from URL: {url}")
    try:
        # Fetch PDF
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Save PDF to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        logger.debug(f"Saved PDF to temporary file: {tmp_path}")
        
        try:
            # Parse PDF using MuPDF
            markdown_content = pymupdf4llm.to_markdown(tmp_path)
            
            # Clean up the markdown content
            cleaned_markdown = clean_markdown(markdown_content)
            
            logger.debug(f"Successfully parsed PDF. Content length: {len(cleaned_markdown)}")
            return cleaned_markdown
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            logger.debug("Removed temporary PDF file")
            
    except Exception as e:
        logger.error(f"Error parsing PDF from {url}: {str(e)}", exc_info=True)
        return None

def is_pdf_url(url, content_type=None):
    """Check if URL points to a PDF"""
    return (url.lower().endswith('.pdf') or 
            (content_type and 'application/pdf' in content_type.lower()))

def fetch_and_parse_url(url, pdf_only=False):
    """
    Fetch URL content and parse it to markdown
    Args:
        url: URL to fetch and parse
        pdf_only: If True, only process PDF files
    Returns:
        Parsed markdown content or None if failed
    """
    logger.debug(f"Fetching and parsing URL: {url} (PDF only: {pdf_only})")
    try:
        # Check if URL is PDF
        if url.lower().endswith('.pdf'):
            logger.debug("Processing as PDF document")
            return fetch_and_parse_pdf(url)
            
        # Handle web pages
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.debug(f"Successfully fetched URL. Content length: {len(response.text)}")
        
        # Check content type for PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' in content_type:
            logger.debug("Content-type indicates PDF, processing as PDF document")
            return fetch_and_parse_pdf(url)
            
        # If pdf_only is True, skip non-PDF content
        if pdf_only:
            logger.debug("Skipping non-PDF content")
            return None
        
        # Handle Wikipedia pages
        if 'wikipedia.org' in url:
            logger.debug("Processing as Wikipedia page")
            cleaned_html = clean_wikipedia_content(response.text)
        else:
            logger.debug("Processing as generic webpage")
            cleaned_html = response.text
            
        if not cleaned_html:
            logger.warning(f"No content extracted from {url}")
            return None
            
        # Convert to markdown
        markdown_content = html_to_markdown(cleaned_html)
        
        # Clean up markdown
        cleaned_markdown = clean_markdown(markdown_content)
        
        logger.debug(f"Successfully parsed URL. Final content length: {len(cleaned_markdown)}")
        return cleaned_markdown
        
    except Exception as e:
        logger.error(f"Error fetching/parsing {url}: {str(e)}", exc_info=True)
        return None

def parse_block_contents(blocks, pdf_only=False):
    """
    Parse content for a list of blocks
    Args:
        blocks: List of blocks to parse
        pdf_only: If True, only process PDF files
    Returns:
        Dictionary of url -> parsed content
    """
    logger.info(f"Starting to parse {len(blocks)} blocks (PDF only: {pdf_only})")
    parsed_content = {}
    
    for i, block in enumerate(blocks, 1):
        logger.debug(f"Processing block {i}/{len(blocks)}")
        if not block.get("source") or not block["source"].get("url"):
            logger.debug(f"Skipping block {i} - no source URL")
            continue
            
        url = block["source"]["url"]
        content_type = block["source"].get("content_type", "")
        
        # Skip non-PDF files if pdf_only is True
        if pdf_only and not is_pdf_url(url, content_type):
            logger.debug(f"Skipping non-PDF URL: {url}")
            continue
            
        if url not in parsed_content:
            logger.debug(f"Parsing new URL: {url}")
            content = fetch_and_parse_url(url, pdf_only=pdf_only)
            if content:
                parsed_content[url] = content
                logger.debug(f"Successfully parsed content for {url}")
            else:
                logger.warning(f"Failed to parse content for {url}")
    
    logger.info(f"Completed parsing {len(parsed_content)} unique URLs")
    return parsed_content