# LLM Place

LLM Place enables any github user to modify `index.html` by submitting a natural language change requests. 

Create an issues with a `prompt` label, and describe the desired modifications in the body. The system will automatically update the webpage based on the instructions.

The webpage index.html is hosted at https://mnaei.github.io/LLMPlace/

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
