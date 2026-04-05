# Add LoreConvo Audit Trail to Local Model Preprocessing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--save-to-loreconvo` flag to local_model_preprocess.py so preprocessing actions are automatically logged to LoreConvo for audit trail and debugging during Meg/Brock testing.

**Architecture:** When `--save-to-loreconvo` flag is passed, after the local model completes, the script calls `save_to_loreconvo.py` to log the preprocessing action with agent/task/output details. This creates a timestamped record in LoreConvo with surface='preprocessing' for later review and debugging.

**Tech Stack:** Python subprocess for calling save_to_loreconvo.py, JSON for packaging data, argparse for new flag.

---

## File Structure

**Files to modify:**
- `scripts/local_model_preprocess.py` - Add flag parsing, save logic after Ollama call
- `tests/scripts/test_local_model_preprocess.py` - Add tests for save flag, mocking subprocess calls
- Updated agent prompts (will be done in separate tasks):
  - `docs/internal/other documentation/agent prompts/meg.md` - Add `--save-to-loreconvo` flag
  - `docs/internal/other documentation/agent prompts/brock.md` - Add `--save-to-loreconvo` flag
- `scripts/README.md` - Document the new flag and audit trail feature

---

## Task 1: Add --save-to-loreconvo Flag to Argument Parser

**Files:**
- Modify: `scripts/local_model_preprocess.py:41-65` (parse_arguments function)

- [ ] **Step 1: Read parse_arguments function**

Read the function to understand current argument structure.

- [ ] **Step 2: Add new argument to parser**

In the `parse_arguments()` function, add the flag after the existing optional arguments:

```python
parser.add_argument(
    '--save-to-loreconvo',
    action='store_true',
    default=False,
    help='Save preprocessing action to LoreConvo for audit trail (optional)'
)
```

Add this after the `--output-format` argument, before `return parser.parse_args()`.

- [ ] **Step 3: Verify argument is accessible**

Run: `python3 scripts/local_model_preprocess.py --help | grep -A 2 "save-to-loreconvo"`

Expected: Flag appears in help output with description.

- [ ] **Step 4: Commit**

```bash
git add scripts/local_model_preprocess.py
git commit -m "feat: add --save-to-loreconvo flag to argument parser"
```

---

## Task 2: Implement save_to_loreconvo Logic in main()

**Files:**
- Modify: `scripts/local_model_preprocess.py:main()` function

- [ ] **Step 1: Add save_to_loreconvo function**

Add this helper function before `main()`:

```python
def save_preprocessing_to_loreconvo(agent: str, task: str, output: str, model: str) -> bool:
    """
    Save preprocessing action to LoreConvo for audit trail.

    Args:
        agent: Agent name (meg, brock, etc.)
        task: Task name (test_scenarios, file_screening, etc.)
        output: The preprocessing output (result from local model)
        model: Model used (qwen3.5:9b, gemma4)

    Returns:
        True if save successful, False if failed (logged as warning)
    """
    from datetime import datetime
    import json

    try:
        # Create title and summary
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = f"Preprocessing: {agent} {task} ({now})"
        summary = f"Local model preprocessing completed.\nAgent: {agent}\nTask: {task}\nModel: {model}\n\nOutput preview:\n{output[:500]}"

        # Call save_to_loreconvo script
        result = subprocess.run(
            [
                'python3',
                'scripts/save_to_loreconvo.py',
                '--title', title,
                '--surface', 'preprocessing',
                '--summary', summary,
                '--tags', json.dumps(['preprocessing', f'agent:{agent}', f'task:{task}']),
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            logger.debug(f"Saved preprocessing action to LoreConvo: {title}")
            return True
        else:
            logger.warning(f"Failed to save to LoreConvo: {result.stderr}")
            return False

    except Exception as e:
        logger.warning(f"Error saving to LoreConvo: {e}")
        return False
```

- [ ] **Step 2: Call save function in main() after Ollama succeeds**

In the `main()` function, after the Ollama call succeeds and we have output, add:

```python
# Save to LoreConvo if requested
if args.save_to_loreconvo and result is not None:
    save_preprocessing_to_loreconvo(
        agent=args.agent,
        task=args.task,
        output=result,
        model=args.model
    )
```

Add this BEFORE `print(result)` so the save happens while we still have the output.

- [ ] **Step 3: Test the function exists**

Run: `python3 scripts/local_model_preprocess.py --help`

Expected: Flag appears, no import errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/local_model_preprocess.py
git commit -m "feat: add save_preprocessing_to_loreconvo function and integrate into main()"
```

---

## Task 3: Add Unit Tests for save_to_loreconvo Flag

**Files:**
- Modify: `tests/scripts/test_local_model_preprocess.py`

- [ ] **Step 1: Add test for flag in TestArgumentParsing**

Add this test to the TestArgumentParsing class:

```python
def test_parse_save_to_loreconvo_flag_false_by_default(self):
    args = parse_arguments(['--agent', 'meg', '--task', 'test_scenarios',
                          '--input', 'test.txt', '--model', 'qwen3.5:9b'])
    assert args.save_to_loreconvo is False

def test_parse_save_to_loreconvo_flag_true_when_passed(self):
    args = parse_arguments(['--agent', 'meg', '--task', 'test_scenarios',
                          '--input', 'test.txt', '--model', 'qwen3.5:9b',
                          '--save-to-loreconvo'])
    assert args.save_to_loreconvo is True
```

- [ ] **Step 2: Add test for save function success**

Add to the test file (can be in a new TestSaveFunction class or TestIntegration):

```python
@patch('subprocess.run')
def test_save_preprocessing_to_loreconvo_success(self, mock_run):
    """Test successful save to LoreConvo"""
    mock_run.return_value = MagicMock(returncode=0, stderr='')

    result = save_preprocessing_to_loreconvo(
        agent='meg',
        task='test_scenarios',
        output='Test scenario output here',
        model='qwen3.5:9b'
    )

    assert result is True
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert 'save_to_loreconvo.py' in call_args
    assert '--surface' in call_args
    assert 'preprocessing' in call_args

@patch('subprocess.run')
def test_save_preprocessing_to_loreconvo_failure(self, mock_run):
    """Test graceful handling when save fails"""
    mock_run.return_value = MagicMock(returncode=1, stderr='DB error')

    result = save_preprocessing_to_loreconvo(
        agent='brock',
        task='file_screening',
        output='File output',
        model='qwen3.5:9b'
    )

    assert result is False

@patch('subprocess.run')
def test_save_preprocessing_to_loreconvo_timeout(self, mock_run):
    """Test graceful handling when save times out"""
    mock_run.side_effect = subprocess.TimeoutExpired('cmd', 10)

    result = save_preprocessing_to_loreconvo(
        agent='meg',
        task='test_scenarios',
        output='Output',
        model='qwen3.5:9b'
    )

    assert result is False
```

- [ ] **Step 3: Add integration test with flag**

Add to TestIntegration:

```python
@patch('save_preprocessing_to_loreconvo')
@patch('subprocess.run')
def test_main_with_save_to_loreconvo_flag(self, mock_ollama, mock_save):
    """Test main() calls save function when flag is set"""
    # Setup mocks
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('test content')
        input_file = f.name

    try:
        mock_ollama.return_value = MagicMock(
            stdout='Test output\n',
            returncode=0
        )
        mock_save.return_value = True

        # Simulate args with --save-to-loreconvo
        with patch('sys.argv', ['prog', '--agent', 'meg', '--task', 'test_scenarios',
                               '--input', input_file, '--model', 'qwen3.5:9b',
                               '--save-to-loreconvo']):
            # This should not raise (exit code would be called in real run)
            pass

    finally:
        Path(input_file).unlink()
```

- [ ] **Step 4: Run tests to verify new tests pass**

Run: `python3 -m pytest tests/scripts/test_local_model_preprocess.py::TestArgumentParsing::test_parse_save_to_loreconvo_flag_false_by_default -v`

Expected: PASS

Run: `python3 -m pytest tests/scripts/test_local_model_preprocess.py -k "save_to_loreconvo" -v`

Expected: All save-related tests pass.

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/scripts/test_local_model_preprocess.py -v`

Expected: All tests pass (original 68 + new 4-5 tests = 72+ tests).

- [ ] **Step 6: Commit**

```bash
git add tests/scripts/test_local_model_preprocess.py
git commit -m "test: add tests for --save-to-loreconvo flag and save function"
```

---

## Task 4: Update Meg's Agent Prompt

**Files:**
- Modify: `docs/internal/other documentation/agent prompts/meg.md`

- [ ] **Step 1: Add flag to preprocessing command**

In Meg's prompt, find the line:
```
python scripts/local_model_preprocess.py --agent meg --task test_scenarios --input changed_files.txt --model qwen3.5:9b
```

Change it to:
```
python scripts/local_model_preprocess.py --agent meg --task test_scenarios --input changed_files.txt --model qwen3.5:9b --save-to-loreconvo
```

- [ ] **Step 2: Add note about audit trail**

After the preprocessing command, add:
```
(This saves the preprocessing output to LoreConvo for audit trail and debugging.)
```

- [ ] **Step 3: Verify syntax**

Read the file to ensure the command is properly formatted and readable.

- [ ] **Step 4: Commit**

```bash
git add docs/internal/other\ documentation/agent\ prompts/meg.md
git commit -m "feat: add --save-to-loreconvo flag to Meg preprocessing step"
```

---

## Task 5: Update Brock's Agent Prompt

**Files:**
- Modify: `docs/internal/other documentation/agent prompts/brock.md`

- [ ] **Step 1: Add flag to preprocessing command**

In Brock's prompt, find the line:
```
python scripts/local_model_preprocess.py --agent brock --task file_screening --input all_changed_files.txt --model qwen3.5:9b --output-format json
```

Change it to:
```
python scripts/local_model_preprocess.py --agent brock --task file_screening --input all_changed_files.txt --model qwen3.5:9b --output-format json --save-to-loreconvo
```

- [ ] **Step 2: Add note about audit trail**

After the preprocessing command, add:
```
(This saves the preprocessing output and file categorization to LoreConvo for audit trail and debugging.)
```

- [ ] **Step 3: Verify syntax**

Read the file to ensure the command is properly formatted and readable.

- [ ] **Step 4: Commit**

```bash
git add docs/internal/other\ documentation/agent\ prompts/brock.md
git commit -m "feat: add --save-to-loreconvo flag to Brock preprocessing step"
```

---

## Task 6: Update README Documentation

**Files:**
- Modify: `scripts/README.md`

- [ ] **Step 1: Add section about LoreConvo audit trail**

Find the "CLI Usage" section. After the "Exit Codes" table, add:

```markdown
### Optional: Audit Trail with LoreConvo

To automatically save preprocessing actions to LoreConvo for debugging and audit trail, pass the `--save-to-loreconvo` flag:

```bash
python scripts/local_model_preprocess.py --agent meg --task test_scenarios \
  --input code_changes.txt --model qwen3.5:9b --save-to-loreconvo
```

This logs the preprocessing action to LoreConvo with:
- **Surface:** preprocessing
- **Tags:** preprocessing, agent:meg, task:test_scenarios
- **Summary:** Preview of output and execution details

Useful for debugging, testing, and maintaining an audit trail of all preprocessing work.

If `save_to_loreconvo.py` is unavailable or fails, the script logs a warning but continues — preprocessing is not blocked.
```

- [ ] **Step 2: Update example commands**

In the "Examples" section, add one more example showing the flag:

```markdown
#### Example 3: Brock with Audit Trail

```bash
python scripts/local_model_preprocess.py \
  --agent brock \
  --task file_screening \
  --input all_files.txt \
  --model qwen3.5:9b \
  --output-format json \
  --save-to-loreconvo
```

Output:
```json
{
  "flagged": ["auth.py", "database.py"],
  "safe": ["test_helpers.py", "config.yaml"],
  "reason": "auth.py modified crypto, database.py modified query logic"
}
```

(This result is also saved to LoreConvo with surface='preprocessing' for later review.)
```

- [ ] **Step 3: Verify formatting**

Read the entire README to ensure it's clear and examples are properly formatted.

- [ ] **Step 4: Commit**

```bash
git add scripts/README.md
git commit -m "docs: add --save-to-loreconvo flag documentation and examples"
```

---

## Task 7: Verify End-to-End

**No files modified — testing only**

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/scripts/test_local_model_preprocess.py -v`

Expected: All tests pass (72+ tests).

- [ ] **Step 2: Verify git log shows all commits**

Run: `git log --oneline -6`

Expected: Last 6 commits include:
1. docs: add --save-to-loreconvo flag documentation
2. feat: add --save-to-loreconvo flag to Brock preprocessing step
3. feat: add --save-to-loreconvo flag to Meg preprocessing step
4. test: add tests for --save-to-loreconvo flag
5. feat: add save_preprocessing_to_loreconvo function
6. feat: add --save-to-loreconvo flag to argument parser

- [ ] **Step 3: Verify flag appears in help**

Run: `python3 scripts/local_model_preprocess.py --help | grep -A 3 "save-to-loreconvo"`

Expected: Flag description appears.

- [ ] **Step 4: Final status check**

Run: `git status`

Expected: Working tree clean (all changes committed).

---

## Success Criteria

✅ All tests pass (72+ tests)
✅ `--save-to-loreconvo` flag is recognized by argparse
✅ Flag defaults to False (backward compatible)
✅ When flag is passed, script calls `save_to_loreconvo.py` after Ollama succeeds
✅ LoreConvo save failures are logged as warnings but don't block preprocessing
✅ Meg and Brock agent prompts use the new flag
✅ README documents the feature with examples
✅ All changes committed to master

---
