"""QA Pipeline service for test validation and LLM judging."""
import subprocess
import tempfile
import shutil
import os
import json
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.models import Trace, QAResult, Event
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


async def run_qa_pipeline(trace: Trace, db: Session) -> QAResult:
    """
    Run the complete QA pipeline for a trace.
    
    This includes:
    1. Docker test validation
    2. LLM reasoning evaluation
    3. Storing results in database
    """
    try:
        # 1. Run tests in Docker container
        tests_passed, test_output = await run_tests_in_docker(trace.repo_url, trace.events)
        
        # 2. Call LLM judge for reasoning evaluation
        reasoning_score, judge_comments = await evaluate_reasoning_with_llm(trace)
        
        # 3. Create QAResult record
        qa_result = QAResult(
            trace_id=trace.trace_id,
            tests_passed=1 if tests_passed else 0,
            reasoning_score=reasoning_score,
            judge_comments=judge_comments,
            test_output=test_output,
            qa_timestamp=datetime.now().isoformat()
        )
        db.add(qa_result)
        db.commit()
        db.refresh(qa_result)
        return qa_result
    except Exception as e:
        # If QA pipeline fails, create a failed result
        qa_result = QAResult(
            trace_id=trace.trace_id,
            tests_passed=0,
            reasoning_score=0.0,
            judge_comments=f"QA pipeline failed: {str(e)}",
            test_output=str(e),
            qa_timestamp=datetime.now().isoformat()
        )
        db.add(qa_result)
        db.commit()
        db.refresh(qa_result)
        return qa_result


async def run_tests_in_docker(repo_url: str, events: List[Event]) -> tuple[bool, str]:
    """
    Run the repository's test suite in a Docker container.
    
    Args:
        repo_url: URL of the repository
        events: List of events containing code edits
        
    Returns:
        Tuple of (tests_passed: bool, test_output: str)
    """
    temp_dir = None
    try:
        # 1. Clone repository
        temp_dir = await clone_repository(repo_url)
        
        # 2. Apply diffs from edit events
        await apply_diffs(temp_dir, events)
        
        # 3. Build Docker container (if Dockerfile exists)
        image_name = await build_docker_container(temp_dir)
        
        # 4. Run test suite
        exit_code, test_output = await run_tests_in_container(image_name, temp_dir)
        
        # 5. Cleanup Docker image
        try:
            subprocess.run(
                ["docker", "rmi", "-f", image_name],
                capture_output=True,
                timeout=10
            )
        except:
            pass  # Ignore cleanup errors
        
        # 6. Return results
        tests_passed = exit_code == 0
        return tests_passed, test_output
        
    except Exception as e:
        error_msg = f"Error running tests: {str(e)}"
        return False, error_msg
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass  # Ignore cleanup errors


async def clone_repository(repo_url: str) -> str:
    """Clone repository to a temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="trace_repo_")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to clone repository: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise Exception("Repository clone timed out")


async def apply_diffs(temp_dir: str, events: List[Event]):
    """Apply code diffs from edit events to the repository."""
    for event in events:
        if event.event_type == "edit":
            try:
                details = json.loads(event.details) if isinstance(event.details, str) else event.details
                file_path = details.get("file", "")
                diff = details.get("diff", "")
                
                if not file_path or not diff:
                    continue
                
                full_path = os.path.join(temp_dir, file_path.lstrip("/"))
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Apply diff using git apply if it's a proper diff format
                if diff.startswith("@@"):
                    # Try to apply as a patch
                    try:
                        patch_file = os.path.join(temp_dir, ".patch")
                        with open(patch_file, "w") as f:
                            f.write(diff)
                        
                        # Try git apply
                        result = subprocess.run(
                            ["git", "-C", temp_dir, "apply", patch_file],
                            capture_output=True,
                            text=True
                        )
                        os.remove(patch_file)
                    except:
                        # Fallback: write the file directly if diff application fails
                        # This is a simplified approach - in production, use proper diff libraries
                        if "change" in details:
                            with open(full_path, "w") as f:
                                # This is a placeholder - proper diff application needed
                                pass
                else:
                    # If not a proper diff, try to write the file content directly
                    # This assumes 'change' contains the full file content
                    if "change" in details:
                        with open(full_path, "w") as f:
                            f.write(details["change"])
            except Exception as e:
                # Log error but continue with other events
                print(f"Error applying diff for event {event.id}: {e}")
                continue


async def build_docker_container(repo_path: str) -> str:
    """
    Build Docker container from repository.
    
    Returns:
        Image name/tag
    """
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    
    # If no Dockerfile, create a basic one for common languages
    if not os.path.exists(dockerfile_path):
        # Try to detect language and create appropriate Dockerfile
        if os.path.exists(os.path.join(repo_path, "package.json")):
            # Node.js project
            dockerfile_content = """FROM node:18
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "test"]
"""
        elif os.path.exists(os.path.join(repo_path, "requirements.txt")):
            # Python project
            dockerfile_content = """FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["pytest"]
"""
        elif os.path.exists(os.path.join(repo_path, "pom.xml")):
            # Java/Maven project
            dockerfile_content = """FROM maven:3.8-openjdk-17
WORKDIR /app
COPY . .
RUN mvn test
"""
        else:
            raise ValueError("No Dockerfile found and could not auto-detect project type")
        
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
    
    # Generate unique image name
    import hashlib
    repo_hash = hashlib.md5(repo_path.encode()).hexdigest()[:8]
    image_name = f"trace-test-{repo_hash}"
    
    # Build Docker image
    try:
        result = subprocess.run(
            ["docker", "build", "-t", image_name, repo_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return image_name
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to build Docker image: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise Exception("Docker build timed out")


async def run_tests_in_container(image_name: str, repo_path: str) -> tuple[int, str]:
    """Run tests in Docker container."""
    # Try common test commands
    test_commands = [
        "npm test",
        "python -m pytest",
        "pytest",
        "python -m unittest discover",
        "mvn test",
        "make test",
        "./test.sh"
    ]
    
    for test_cmd in test_commands:
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{repo_path}:/app",
                    "-w", "/app",
                    image_name,
                    "sh", "-c", test_cmd
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            # If command exists and runs (even if tests fail), return the result
            if result.returncode != 127:  # 127 = command not found
                return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "Test execution timed out"
        except Exception:
            continue
    
    # If no test command worked, return error
    return 1, "No test command found or all test commands failed"


async def evaluate_reasoning_with_llm(trace: Trace) -> tuple[float, str]:
    """
    Use LLM to evaluate the quality of developer reasoning.
    
    Args:
        trace: The trace containing reasoning events
        
    Returns:
        Tuple of (reasoning_score: float, judge_comments: str)
    """
    try:
        # 1. Extract reasoning events from trace
        reasoning_events = [e for e in trace.events if e.event_type == "reasoning"]
        edit_events = [e for e in trace.events if e.event_type == "edit"]
        
        if not reasoning_events:
            # If no reasoning events, return default score
            return 2.5, "No reasoning events found in trace"
        
        # 2. Construct prompt with rubric
        prompt = construct_prompt(trace, reasoning_events, edit_events)
        
        # 3. Call OpenAI API
        response = await call_openai_api(prompt)
        
        # 4. Parse response and extract score/comments
        reasoning_score, judge_comments = parse_response(response)
        
        # 5. Return results
        return reasoning_score, judge_comments
    except Exception as e:
        # If LLM evaluation fails, return default score
        return 2.5, f"LLM evaluation failed: {str(e)}"


def construct_prompt(trace: Trace, reasoning_events: List[Event], edit_events: List[Event]) -> str:
    """
    Construct a prompt for the LLM to evaluate the reasoning of the developer.
    """
    # Extract reasoning details
    reasoning_texts = []
    for event in reasoning_events:
        try:
            details = json.loads(event.details) if isinstance(event.details, str) else event.details
            reasoning_texts.append({
                "text": details.get("text", ""),
                "type": details.get("reasoning_type", "unknown"),
                "confidence": details.get("confidence", "medium"),
                "timestamp": event.event_timestamp
            })
        except:
            continue
    
    # Extract edit summaries
    edit_summaries = []
    for event in edit_events[:5]:  # Limit to first 5 edits
        try:
            details = json.loads(event.details) if isinstance(event.details, str) else event.details
            edit_summaries.append({
                "file": details.get("file", ""),
                "change": details.get("change", "")[:100]  # Truncate
            })
        except:
            continue
    
    prompt = f"""You are an AI judge evaluating the quality of a developer's reasoning process while fixing a bug.

Bug Description: {trace.bug_description}

Reasoning Events:
{json.dumps(reasoning_texts, indent=2)}

Code Changes Made:
{json.dumps(edit_summaries, indent=2)}

Evaluate the developer's reasoning based on these criteria (1-5 scale):
1. Clarity of hypothesis: How clear and specific were their hypotheses about the bug?
2. Quality of alternatives: Did they consider alternative approaches?
3. Logical reasoning chain: Was their reasoning process logical and well-structured?
4. Confidence calibration: Did their confidence levels match the quality of their reasoning?
5. Problem-solving approach: How effective was their overall approach?

Provide your evaluation in the following JSON format:
{{
    "reasoning_score": <float between 1.0 and 5.0>,
    "judge_comments": "<detailed explanation of your evaluation>"
}}

Respond ONLY with valid JSON, no additional text."""
    
    return prompt


async def call_openai_api(prompt: str) -> str:
    """
    Call the OpenAI API to evaluate the reasoning of the developer.
    """
    try:
        # Use the new OpenAI API (v1.x)
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer evaluating developer reasoning. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API call failed: {str(e)}")


def parse_response(response: str) -> tuple[float, str]:
    """
    Parse the response from the OpenAI API to extract the reasoning score and judge comments.
    """
    try:
        # Try to extract JSON from response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON
        data = json.loads(response)
        
        reasoning_score = float(data.get("reasoning_score", 2.5))
        judge_comments = data.get("judge_comments", "No comments provided")
        
        # Clamp score to valid range
        reasoning_score = max(1.0, min(5.0, reasoning_score))
        
        return reasoning_score, judge_comments
    except json.JSONDecodeError:
        # Fallback parsing if JSON parsing fails
        try:
            # Try to extract score from text
            if "reasoning_score" in response.lower():
                score_str = response.split("reasoning_score")[1].split(":")[1].split(",")[0].strip()
                reasoning_score = float(score_str.replace('"', '').replace("'", ""))
            else:
                reasoning_score = 2.5
            
            if "judge_comments" in response.lower():
                comments_str = response.split("judge_comments")[1].split(":")[1].strip()
                judge_comments = comments_str.replace('"', '').replace("'", "").strip()
            else:
                judge_comments = response[:500]  # Use first 500 chars as comments
            
            reasoning_score = max(1.0, min(5.0, reasoning_score))
            return reasoning_score, judge_comments
        except:
            # Ultimate fallback
            return 2.5, f"Failed to parse LLM response: {response[:200]}"
