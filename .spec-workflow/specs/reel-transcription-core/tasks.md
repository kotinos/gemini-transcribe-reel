# Tasks: Reel Transcription Core

## 1.0 Input and Validation

- [ ] 1.1 Verify URL validation parity between CLI and web paths
- [ ] 1.2 Confirm file-based batch parsing handles comments/empty lines
- [ ] 1.3 Add/adjust tests for malformed and boundary-case URLs

## 2.0 Download and Media Prep

- [ ] 2.1 Review download error mapping for timeout/no-media cases
- [ ] 2.2 Validate compression threshold and target behavior (>20 MB -> ~18 MB)
- [ ] 2.3 Confirm temp artifact cleanup on all failure paths

## 3.0 Gemini Transcription Flow

- [ ] 3.1 Validate upload/poll/generate/delete lifecycle behavior
- [ ] 3.2 Ensure timeout and failed-state handling stays deterministic
- [ ] 3.3 Verify missing/invalid API key behavior remains explicit

## 4.0 Batch and Rate Limiting

- [ ] 4.1 Confirm fixed delay is applied between batch items
- [ ] 4.2 Ensure batch returns per-item success/error structures
- [ ] 4.3 Verify partial-failure batches still complete remaining items

## 5.0 CLI + Web Output Consistency

- [ ] 5.1 Align user-facing error language where practical
- [ ] 5.2 Confirm stdout/stderr usage remains scripting-friendly
- [ ] 5.3 Ensure web JSON contract remains stable for frontend display

## 6.0 Verification

- [ ] 6.1 Run targeted unit tests for touched behaviors
- [ ] 6.2 Run full `test_transcribe.py` suite
- [ ] 6.3 Regenerate coverage report and validate no major regression

## Definition of Done

- [ ] All relevant tests pass
- [ ] No regression in documented error code contract
- [ ] Steering alignment maintained with:
  - `.spec-workflow/steering/product.md`
  - `.spec-workflow/steering/tech.md`
  - `.spec-workflow/steering/structure.md`
