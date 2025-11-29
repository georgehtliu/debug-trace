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
        
        # 2. Call enhanced LLM judge for reasoning evaluation (with test results)
        evaluation_result = await evaluate_reasoning_with_llm(trace, tests_passed, test_output)
        reasoning_score = evaluation_result["reasoning_score"]
        judge_comments = evaluation_result["judge_comments"]
        detailed_scores = json.dumps(evaluation_result.get("detailed_scores", {}))
        strengths = json.dumps(evaluation_result.get("strengths", []))
        weaknesses = json.dumps(evaluation_result.get("weaknesses", []))
        recommendations = json.dumps(evaluation_result.get("recommendations", []))
        
        # 3. Create QAResult record with enhanced fields
        qa_result = QAResult(
            trace_id=trace.trace_id,
            tests_passed=1 if tests_passed else 0,
            reasoning_score=reasoning_score,
            judge_comments=judge_comments,
            test_output=test_output,
            qa_timestamp=datetime.now().isoformat(),
            detailed_scores=detailed_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
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


async def evaluate_reasoning_with_llm(trace: Trace, tests_passed: bool, test_output: str) -> dict:
    """
    Enhanced LLM evaluation that considers full context including test results.
    
    Args:
        trace: The trace containing reasoning events
        tests_passed: Whether the tests passed
        test_output: Output from test execution
        
    Returns:
        Dictionary with reasoning_score, judge_comments, detailed_scores, strengths, weaknesses, recommendations
    """
    try:
        # 1. Extract all event types
        reasoning_events = [e for e in trace.events if e.event_type == "reasoning"]
        command_events = [e for e in trace.events if e.event_type == "command"]
        edit_events = [e for e in trace.events if e.event_type == "edit"]
        
        if not reasoning_events:
            # If no reasoning events, return default result
            return {
                "reasoning_score": 2.5,
                "judge_comments": "No reasoning events found in trace",
                "detailed_scores": {},
                "strengths": [],
                "weaknesses": ["No reasoning events were recorded"],
                "recommendations": ["Consider adding reasoning events to document your thought process"]
            }
        
        # 2. Build reasoning-action chains (temporal relationships)
        reasoning_chains = build_reasoning_chains(reasoning_events, command_events, edit_events)
        
        # 3. Construct enhanced prompt with full context
        prompt = construct_enhanced_prompt(trace, reasoning_chains, tests_passed, test_output)
        
        # 4. Call OpenAI API with structured output
        response = await call_openai_api_structured(prompt)
        
        # 5. Return structured results
        return response
    except Exception as e:
        # If LLM evaluation fails, return default result
        return {
            "reasoning_score": 2.5,
            "judge_comments": f"LLM evaluation failed: {str(e)}",
            "detailed_scores": {},
            "strengths": [],
            "weaknesses": [f"Evaluation error: {str(e)}"],
            "recommendations": []
        }


def build_reasoning_chains(reasoning_events: List[Event], command_events: List[Event], edit_events: List[Event]) -> List[dict]:
    """
    Build temporal chains showing reasoning → action → result relationships.
    
    Returns:
        List of chains, each containing reasoning event and subsequent action
    """
    # Sort all events by timestamp
    all_events = sorted(
        reasoning_events + command_events + edit_events,
        key=lambda e: e.event_timestamp
    )
    
    chains = []
    current_reasoning = None
    
    for event in all_events:
        if event.event_type == "reasoning":
            current_reasoning = event
        elif current_reasoning and event.event_type in ["command", "edit"]:
            # Extract details for formatting
            try:
                reasoning_details = json.loads(current_reasoning.details) if isinstance(current_reasoning.details, str) else current_reasoning.details
                action_details = json.loads(event.details) if isinstance(event.details, str) else event.details
                
                chains.append({
                    "reasoning": {
                        "text": reasoning_details.get("text", ""),
                        "type": reasoning_details.get("reasoning_type", "unknown"),
                        "confidence": reasoning_details.get("confidence", "medium"),
                        "timestamp": current_reasoning.event_timestamp
                    },
                    "action": {
                        "type": event.event_type,
                        "timestamp": event.event_timestamp,
                        "details": action_details
                    }
                })
            except:
                continue
    
    return chains


def format_reasoning_chains(chains: List[dict]) -> str:
    """Format reasoning chains for prompt display."""
    if not chains:
        return "No reasoning-action chains found."
    
    formatted = []
    for i, chain in enumerate(chains, 1):
        reasoning = chain["reasoning"]
        action = chain["action"]
        
        formatted.append(f"Chain {i}:")
        formatted.append(f"  Reasoning ({reasoning['type']}, confidence: {reasoning['confidence']}):")
        formatted.append(f"    {reasoning['text']}")
        formatted.append(f"  → Action ({action['type']}):")
        if action["type"] == "command":
            formatted.append(f"    Command: {action['details'].get('command', 'N/A')}")
            formatted.append(f"    Output: {action['details'].get('output', 'N/A')[:200]}")
        elif action["type"] == "edit":
            formatted.append(f"    File: {action['details'].get('file', 'N/A')}")
            formatted.append(f"    Change: {action['details'].get('change', 'N/A')[:100]}")
        formatted.append("")
    
    return "\n".join(formatted)


def construct_enhanced_prompt(trace: Trace, reasoning_chains: List[dict], tests_passed: bool, test_output: str) -> str:
    """
    Construct an enhanced prompt for the LLM with full context including test results.
    """
    chains_text = format_reasoning_chains(reasoning_chains)
    test_output_truncated = test_output[:500] if test_output else "N/A"
    
    prompt = f"""You are an expert code reviewer evaluating a developer's debugging reasoning process.

BUG DESCRIPTION:
{trace.bug_description}

REASONING-ACTION CHAINS (showing how reasoning led to actions):
{chains_text}

TEST RESULTS:
- Tests Passed: {tests_passed}
- Test Output: {test_output_truncated}

EVALUATION RUBRIC (score each 1-5, then provide weighted overall score):

1. HYPOTHESIS QUALITY (20% weight)
   - Specificity: Were hypotheses specific and actionable?
   - Root Cause Analysis: Did they identify root causes vs symptoms?
   - Testability: Were hypotheses testable?

2. REASONING CHAIN QUALITY (25% weight)
   - Logical Flow: Clear progression from observation → hypothesis → test → conclusion?
   - Building on Evidence: Did reasoning build on previous insights?
   - Avoiding Fallacies: Were logical fallacies avoided?

3. ALTERNATIVE EXPLORATION (15% weight)
   - Multiple Approaches: Did they explore alternatives?
   - Edge Cases: Considered edge cases and boundary conditions?
   - Critical Thinking: Evidence of questioning assumptions?

4. ACTION-REASONING ALIGNMENT (20% weight)
   - Justified Actions: Did commands/edits follow from reasoning?
   - Hypothesis Testing: Were actions designed to test hypotheses?
   - Efficiency: Minimal unnecessary exploration?

5. CONFIDENCE CALIBRATION (10% weight)
   - Evidence-Based: Did confidence match evidence quality?
   - Appropriate Uncertainty: Were they uncertain when appropriate?
   - Learning: Did they update confidence based on results?

6. EFFICIENCY (10% weight)
   - Direct Path: Was solution reached efficiently?
   - Learning from Failures: Did they learn from failed attempts?
   - Unnecessary Detours: Minimal wasted effort?

OUTPUT FORMAT (JSON):
{{
    "detailed_scores": {{
        "hypothesis_quality": <float 1.0-5.0>,
        "reasoning_chain": <float 1.0-5.0>,
        "alternative_exploration": <float 1.0-5.0>,
        "action_reasoning_alignment": <float 1.0-5.0>,
        "confidence_calibration": <float 1.0-5.0>,
        "efficiency": <float 1.0-5.0>
    }},
    "reasoning_score": <weighted average float 1.0-5.0>,
    "judge_comments": "<detailed explanation with specific examples from the trace>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"],
    "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}

Respond ONLY with valid JSON."""
    
    return prompt


async def call_openai_api_structured(prompt: str) -> dict:
    """
    Call the OpenAI API with structured output for reliable JSON parsing.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Try structured output first (beta feature)
        try:
            response = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Always respond with valid JSON matching the requested schema."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "reasoning_evaluation",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "detailed_scores": {
                                    "type": "object",
                                    "properties": {
                                        "hypothesis_quality": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                        "reasoning_chain": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                        "alternative_exploration": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                        "action_reasoning_alignment": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                        "confidence_calibration": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                        "efficiency": {"type": "number", "minimum": 1.0, "maximum": 5.0}
                                    },
                                    "required": ["hypothesis_quality", "reasoning_chain", "alternative_exploration", 
                                               "action_reasoning_alignment", "confidence_calibration", "efficiency"]
                                },
                                "reasoning_score": {"type": "number", "minimum": 1.0, "maximum": 5.0},
                                "judge_comments": {"type": "string"},
                                "strengths": {"type": "array", "items": {"type": "string"}},
                                "weaknesses": {"type": "array", "items": {"type": "string"}},
                                "recommendations": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["detailed_scores", "reasoning_score", "judge_comments", 
                                       "strengths", "weaknesses", "recommendations"]
                        }
                    }
                },
                temperature=0.1,  # Lower temperature for more consistent scoring
                max_tokens=2000
            )
            
            return json.loads(response.choices[0].message.content)
        except AttributeError:
            # Fallback to regular API if structured output not available
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Request JSON format
            )
            
            content = response.choices[0].message.content
            return parse_enhanced_response(content)
    except Exception as e:
        raise Exception(f"OpenAI API call failed: {str(e)}")


def parse_enhanced_response(response: str) -> dict:
    """
    Parse enhanced response with detailed scores and structured feedback.
    """
    try:
        # Clean response
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
        
        # Extract and validate fields
        detailed_scores = data.get("detailed_scores", {})
        reasoning_score = float(data.get("reasoning_score", 2.5))
        judge_comments = data.get("judge_comments", "No comments provided")
        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        recommendations = data.get("recommendations", [])
        
        # Clamp score to valid range
        reasoning_score = max(1.0, min(5.0, reasoning_score))
        
        # Validate detailed scores
        for key in detailed_scores:
            detailed_scores[key] = max(1.0, min(5.0, float(detailed_scores[key])))
        
        return {
            "detailed_scores": detailed_scores,
            "reasoning_score": reasoning_score,
            "judge_comments": judge_comments,
            "strengths": strengths if isinstance(strengths, list) else [],
            "weaknesses": weaknesses if isinstance(weaknesses, list) else [],
            "recommendations": recommendations if isinstance(recommendations, list) else []
        }
    except json.JSONDecodeError as e:
        # Fallback: return default structure
        return {
            "detailed_scores": {},
            "reasoning_score": 2.5,
            "judge_comments": f"Failed to parse LLM response: {str(e)}",
            "strengths": [],
            "weaknesses": ["Response parsing failed"],
            "recommendations": []
        }


# Legacy parse_response function removed - now using parse_enhanced_response
