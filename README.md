# LLM Editor

LLM Editor is an automated system that enables users to modify a webpage's `index.html` file hosted on GitHub by submitting natural language change requests. Using GitHub Issues with a `prompt` label, users can describe the desired modifications, and the system will automatically update the webpage based on those instructions.

## How It Works

1. **Issue Submission**  
   Users submit a GitHub Issue labeled `prompt` with natural language instructions in the issue body.

2. **Triggering the Workflow**  
   A GitHub Actions workflow (`.github/workflows/llm-editor.yml`) is triggered by the labeled issue. This workflow:
   - Checks out the repository.
   - Sets up the Python environment.
   - Runs the `llm_editor.py` script.

3. **Processing the Request**  
   The `llm_editor.py` script performs the following:
   - **Fetch Current HTML**: Retrieves the current `index.html` file from the repository.
   - **Construct Prompt**: Combines the current HTML with the natural language instructions provided in the issue.
   - **Call OpenAI API**: Sends the prompt to the OpenAI API to generate updated HTML/CSS/JS code.
   - **Extract Valid HTML**: Uses a Python library to extract only valid HTML tags from the API response.
   - **Commit Changes**: Commits the updated `index.html` directly to the `main` branch.
   - **Comment on Issue**: Posts a comment on the issue containing a link to the commit and a diff of the changes.

4. **Error Handling & Concurrency**  
   - **Robust Error Handling**: The script handles API errors, commit failures, and other potential issues gracefully.
   - **Concurrency Control**: The GitHub Actions workflow leverages concurrency features to prevent race conditions when multiple issues are processed simultaneously.

## Getting Started

### Prerequisites

- **Python 3.x**: Ensure Python is installed on your GitHub Actions runner.
- **GitHub Actions**: The automation is built on GitHub Actions.
- **OpenAI API Key**: Required for interacting with the OpenAI API. Add your API key as a repository secret named `OPENAI_API_KEY`.
- **GitHub Token**: The `GITHUB_TOKEN` provided by GitHub Actions is used to commit changes and post comments.

### Installation

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/yourusername/llm-editor.git
   cd llm-editor
