import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMEngine:
    def __init__(self, provider="openai"):
        self.provider = provider
        self.api_key_set = True
        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                self.api_key_set = False
                print("Warning: OPENAI_API_KEY not set. Using mock feedback.")
            else:
                self.client = OpenAI(api_key=key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        elif provider == "groq":
            key = os.getenv("GROQ_API_KEY")
            if not key:
                self.api_key_set = False
                print("Warning: GROQ_API_KEY not set. Using mock feedback.")
            else:
                self.client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=key
                )
                self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def analyze_code(self, code_content, filename):
        """Analyzes a full file for potential bugs and security issues."""
        if not self.api_key_set:
            return [{"severity": "LOW", "line": 1, "fix_suggestion": "Mock...", "comment": "Mock review (no API key)."}]
        
        prompt = f"""
        Analyze the following code from the file '{filename}' and identify potential bugs, security vulnerabilities, or performance issues.
        For each issue found, specify the severity (LOW, MEDIUM, CRITICAL), the line number, a fix suggestion, and a brief comment.
        Return the result as a JSON object with a key "issues" containing a list of objects.

        Code Content:
        {code_content}

        Response Format:
        {{
            "issues": [
                {{"severity": "CRITICAL", "line": 42, "fix_suggestion": "Explain fix...", "comment": "Explain why..."}},
                ...
            ]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert security auditor and senior engineer. You ALWAYS return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            issues = []
            if isinstance(result, dict):
                if "issues" in result:
                    issues = result["issues"]
                else:
                    issues = [result]
            elif isinstance(result, list):
                issues = result

            final_issues = []
            for issue in issues:
                if isinstance(issue, dict):
                    final_issues.append(issue)
            
            return final_issues
        except Exception as e:
            print(f"DEBUG: Error during full code analysis: {e}")
            return []

    def analyze_diff(self, diff_text):
        if not self.api_key_set:
            return [
                {"severity": "LOW", "line": 1, "fix_suggestion": "Mock fix...", "comment": "This is a mock review because no API key was provided."},
                {"severity": "MEDIUM", "line": 5, "fix_suggestion": "Check logic...", "comment": "Potential issue detected (Mock)."}
            ]
        
        prompt = f"""
        Analyze the following git diff and provide a structured code review.
        For each issue found, specify the severity (LOW, MEDIUM, CRITICAL), the line number (if possible), a fix suggestion, and a brief comment.
        Return the result as a JSON object with a key "issues" containing a list of objects.

        Diff Content:
        {diff_text}

        Response Format:
        {{
            "issues": [
                {{"severity": "CRITICAL", "line": 42, "fix_suggestion": "Explain fix...", "comment": "Explain why..."}},
                ...
            ]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software engineer and security auditor. You ALWAYS return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            print(f"DEBUG: LLM Response Content: {content}")
            result = json.loads(content)
            
            issues = []
            if isinstance(result, dict):
                if "issues" in result:
                    issues = result["issues"]
                else:
                    # In case it returned a single issue or a different dict
                    issues = [result]
            elif isinstance(result, list):
                issues = result

            # Ensure every item in issues is a dict
            final_issues = []
            for issue in issues:
                if isinstance(issue, str):
                    try:
                        final_issues.append(json.loads(issue))
                    except:
                        continue
                elif isinstance(issue, dict):
                    final_issues.append(issue)
            
            return final_issues
        except Exception as e:
            print(f"DEBUG: Error during LLM analysis: {e}")
            return []

if __name__ == "__main__":
    # Test
    engine = LLMEngine(provider="groq")
    test_diff = """
    @@ -1,5 +1,5 @@
    -def add(a, b):
    -    return a + b
    +def add(a, b):
    +    # POTENTIAL BUG: NO TYPE CHECKING
    +    return a + b
    """
    feedback = engine.analyze_diff(test_diff)
    print(json.dumps(feedback, indent=2))
