# Gies College of Business - Enhanced Site Map for LLMs

## Overview

This document explains the purpose, structure, and applications of the `llms-enhanced.txt` file created for Gies College of Business. The enhanced file is a comprehensive, structured representation of the college's website content, optimized for both human readability and Large Language Model (LLM) understanding.

## What is llms-enhanced.txt?

`llms-enhanced.txt` is a semantically structured representation of the Gies College of Business website that:

1. Organizes content hierarchically by topic and section
2. Includes descriptive metadata about each page
3. Provides context and relationships between different parts of the website
4. Enhances navigation with consistent formatting and clear labels
5. Includes structured JSON metadata for automated processing

## Why is this file useful?

### For College Administrators
- **Website Audit**: Provides a comprehensive view of site organization and content
- **Content Management**: Identifies content gaps, overlaps, or inconsistencies
- **Information Architecture**: Shows how website sections relate to each other
- **Accessibility**: Makes website structure understandable at a glance

### For LLM Applications
- **Accurate Information Retrieval**: Helps LLMs (like Claude or ChatGPT) provide accurate responses about Gies programs and services
- **Contextual Understanding**: Enables LLMs to understand relationships between different parts of the college
- **Enhanced Responses**: Improves the quality of AI responses to prospective students, current students, and other stakeholders
- **Resource Optimization**: Reduces the need for LLMs to crawl the entire website repeatedly

### For IT and Web Teams
- **Documentation**: Serves as living documentation of the website structure
- **Development Planning**: Helps identify areas for website improvement
- **SEO Enhancement**: Provides insights for improving search engine optimization

## How to Use the Enhanced File

### For Reference and Planning
1. **Content Audit**: Review the file to understand how your website content is currently organized
2. **Gap Analysis**: Identify missing information or areas needing additional content
3. **Navigation Review**: Evaluate the logical structure of your site based on the hierarchical organization

### For AI and Chatbot Integration
1. **Knowledge Base**: Use as a foundation document for college chatbots or virtual assistants
2. **Training Data**: Incorporate into training materials for custom AI applications
3. **LLM Context**: Provide to LLMs as context when asking questions about Gies College

### For Content Updates
1. **Add New Programs**: Insert new offerings in the appropriate sections, following the established format
2. **Update Information**: Modify descriptions while maintaining the hierarchical structure
3. **Track Changes**: Compare versions over time to see how content has evolved

## File Structure and Features

The file is organized into several key components:

1. **Metadata Header**: JSON block with information about the file itself
2. **Primary Sections**: Major website areas (About, Academic Programs, Student Experience, etc.)
3. **Hierarchical Subsections**: Nested organization of related content
4. **Descriptive Links**: URLs with context about what each page contains
5. **Topic-Based Index**: Cross-references content by subject rather than site structure

## Creating Your Own Enhanced Site Maps

### Prerequisites
- Python 3.7+ installed
- Google API key for Gemini (free tier is sufficient)
- Required Python packages (install with `pip install -r requirements.txt`)

### Running the Script
1. Set your Google API key as an environment variable (recommended):
   ```bash
   export GOOGLE_API_KEY=your_api_key_here
   ```
   
2. Run the script with default settings:
   ```bash
   ./enhanced_crawler.py
   ```
   
3. Or customize with options:
   ```bash
   ./enhanced_crawler.py --url https://your-site.com --name "Your Site Name" --max-pages 200
   ```

### Command Line Options
- `--url`: Website URL to crawl (default: https://giesbusiness.illinois.edu)
- `--name`: Site name for the output files (default: derived from URL)
- `--max-pages`: Maximum pages to crawl (default: 150)
- `--delay`: Delay between requests in seconds (default: 0.2)
- `--skip-enhance`: Skip the enhancement step if you only want the basic site map

### Output Files
- `llms.txt`: Basic site map with pages grouped by URL path
- `llms-enhanced.txt`: AI-enhanced version with hierarchical structure and descriptions

## Maintenance Recommendations

To keep this resource valuable over time:

1. **Regular Updates**: Update quarterly or when significant website changes occur
2. **Version Control**: Maintain the file in a version control system to track changes
3. **Ownership Assignment**: Designate a specific department responsible for maintenance
4. **Automated Validation**: Periodically check links for validity
5. **Enhancement Process**: Continue improving descriptions and adding context

---

*For questions or assistance with this resource, please contact the web development team.*