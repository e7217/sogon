
# Implementation Plan: Local Whisper Model Support

**Branch**: `001-` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/e7217/sogon/specs/001-/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Add local Whisper model inference capability to sogon, enabling users to transcribe audio files using locally-loaded models (CPU, CUDA GPU, or Apple Silicon MPS) instead of relying solely on external APIs. This provides offline transcription, cost elimination, and enhanced data privacy while maintaining 100% backward compatibility with existing API-based workflows. The implementation follows the provider pattern already established in sogon's correction/translation services, introducing FasterWhisperProvider alongside the existing OpenAIProvider.

## Technical Context
**Language/Version**: Python 3.9+ (already required by sogon)
**Primary Dependencies**:
  - Core: FastAPI 0.104+, Uvicorn 0.24+, Pydantic 2.9+, Typer 0.12+
  - Existing: openai>=1.58.1, groq>=0.26.0, yt-dlp, pydub
  - **NEW**: faster-whisper (local inference), torch/torchaudio (GPU support), huggingface-hub (model downloads)
**Storage**: File-based model cache in user's home directory (~/.cache/sogon/models/)
**Testing**: pytest 7.0+ (existing), pytest-mock 3.10+, **NEW**: contract tests for provider interface
**Target Platform**: Linux (initial release), macOS/Windows (phased expansion per NFR-004)
**Project Type**: Single CLI/API application (existing structure: `sogon/`)
**Performance Goals**:
  - GPU: ≥10x realtime (1hr audio → ≤6min transcription)
  - CPU: ≥2x realtime (1hr audio → ≤30min transcription)
  - Model loading: ≤20 seconds for 3GB models
**Constraints**:
  - Backward compatibility: 100% with existing API-based configs
  - Memory management: LRU cache with configurable limits
  - Concurrent jobs: Default 2, user-configurable
  - Offline-capable: Full transcription without network (except initial model download)
**Scale/Scope**:
  - 7 model sizes (tiny → large-v3)
  - 3 compute devices (CPU, CUDA, MPS)
  - ~15-20 new classes/modules
  - User directive: **Unit tests and interfaces first for verification before implementation**

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS (No constitution defined - using best practices)

Since no project-specific constitution exists at `.specify/memory/constitution.md`, applying standard software engineering principles:

✅ **Test-First Development**: User explicitly requested "unit tests and interfaces first for verification"
✅ **Single Responsibility**: Each provider handles one transcription method (API vs local)
✅ **Interface Segregation**: Abstract TranscriptionProvider interface defines contract
✅ **Dependency Injection**: ServiceContainer pattern already exists in sogon
✅ **Open/Closed**: Provider pattern allows adding new transcription methods without modifying existing code
✅ **Backward Compatibility**: Existing API-based workflows remain unchanged (FR-017)
✅ **Simplicity**: Reusing existing architectural patterns from correction/translation services (NFR-007)

**No violations detected** - design aligns with existing sogon architecture and standard SOLID principles.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 1 (Single project) - sogon is a CLI/API application with existing `sogon/` structure

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
Following TDD principles and user directive: **Unit tests and interfaces first**

1. **Contract Test Tasks** (from contracts/):
   - Task: Write TranscriptionProvider interface contract tests
   - Task: Write LocalModelConfiguration schema validation tests
   - [P] Parallel - independent test files

2. **Entity Model Tasks** (from data-model.md):
   - Task: Implement TranscriptionProvider ABC (interface only)
   - Task: Implement LocalModelConfiguration Pydantic model
   - Task: Implement ModelKey value object
   - [P] Parallel - independent modules

3. **Component Unit Test Tasks**:
   - Task: Write ModelManager unit tests (TDD - write tests first)
   - Task: Write DeviceSelector unit tests (TDD - write tests first)
   - Task: Write ResourceMonitor unit tests (TDD - write tests first)
   - Task: Write FasterWhisperProvider unit tests (TDD - write tests first)
   - [P] Parallel - independent test suites

4. **Component Implementation Tasks** (make tests pass):
   - Task: Implement ModelManager (download, cache, LRU eviction)
   - Task: Implement DeviceSelector (CUDA/CPU detection)
   - Task: Implement ResourceMonitor (RAM/VRAM tracking)
   - Task: Implement FasterWhisperProvider (local transcription)
   - Sequential - each depends on previous tests passing

5. **Integration Test Tasks** (from quickstart.md):
   - Task: Write E2E local transcription test (scenario 1)
   - Task: Write backward compatibility test (scenario 2)
   - Task: Write GPU acceleration test (scenario 3)
   - Task: Write concurrent job test (scenarios 4-7)
   - [P] Parallel - independent integration tests

6. **Integration Implementation Tasks**:
   - Task: Wire FasterWhisperProvider into ServiceContainer
   - Task: Add CLI flags for local model config
   - Task: Add environment variable parsing
   - Task: Update TranscriptionService to use provider pattern
   - Sequential - integration order matters

7. **Documentation & Validation Tasks**:
   - Task: Update pyproject.toml with [local] extras
   - Task: Update README with local model section
   - Task: Run all quickstart validation scenarios
   - Task: Run performance benchmarks
   - [P] Parallel - independent documentation

**Ordering Strategy**:
```
Phase 1 (Tests First - Parallel):
  [P] Contract tests
  [P] Entity models
  [P] Unit tests (all components)

Phase 2 (Implementation - Sequential):
  → ModelManager implementation
  → DeviceSelector implementation
  → ResourceMonitor implementation
  → FasterWhisperProvider implementation

Phase 3 (Integration - Mixed):
  [P] Integration test files
  → Wire into ServiceContainer
  → CLI/Config integration

Phase 4 (Validation - Parallel):
  [P] Documentation updates
  [P] Quickstart validation
  [P] Performance benchmarks
```

**Estimated Task Count**: ~35-40 tasks
- Contract tests: 5 tasks
- Entity models: 3 tasks
- Unit tests: 12 tasks (3 per component)
- Implementation: 8 tasks
- Integration tests: 4 tasks
- Integration implementation: 4 tasks
- Documentation: 4 tasks

**Key Principles**:
1. **TDD Strict**: Write ALL tests before ANY implementation
2. **Interfaces First**: Define contracts before concrete classes
3. **Parallel Opportunities**: Mark [P] for ~60% of tasks
4. **Validation Gates**: Each phase must pass tests before next phase

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

**No violations** - Design passes all constitution checks (see Constitution Check section above).

All complexity justified by requirements:
- Provider pattern: Required for FR-016 (switch providers without code changes)
- Model caching: Required for FR-024 (reuse across transcriptions)
- Resource monitoring: Required for FR-021 (prevent memory exhaustion)
- Async concurrency: Required for FR-022 (concurrent transcriptions)

Design follows existing sogon patterns (NFR-007) - no new architectural complexity introduced.


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅ research.md generated
- [x] Phase 1: Design complete (/plan command) ✅ data-model.md, contracts/, quickstart.md, CLAUDE.md
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅ Strategy documented above
- [x] Phase 3: Tasks generated (/tasks command) ✅ tasks.md with 31 TDD-ordered tasks
- [ ] Phase 4: Implementation complete - **READY TO START**
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅ (7 clarifications answered in spec)
- [x] Complexity deviations documented ✅ (No violations - see Complexity Tracking)

**Artifacts Generated**:
- [x] `/specs/001-/plan.md` - This file
- [x] `/specs/001-/research.md` - Technical decisions and library selection
- [x] `/specs/001-/data-model.md` - Entity definitions and relationships
- [x] `/specs/001-/contracts/transcription_provider_interface.py` - Provider ABC contract
- [x] `/specs/001-/contracts/local_model_config_schema.py` - Config schema contract
- [x] `/specs/001-/quickstart.md` - User validation scenarios
- [x] `/home/e7217/sogon/CLAUDE.md` - Agent context file updated
- [x] `/specs/001-/tasks.md` - 31 implementation tasks in TDD order

**Next Step**: Begin implementation following tasks.md (Task 1: Project structure setup)

---
*Based on SOLID principles - No project-specific constitution defined*
