- # Delegation Card

  ## Task

  Build a bounded, repeatable Research Update job that collects recent AI-related updates from selected official sources and produces a concise Markdown digest together with observable execution evidence.

  Use the following official sources:

  - Anthropic News: https://www.anthropic.com/news
  - Anthropic Engineering: https://www.anthropic.com/engineering
  - OpenAI News: https://openai.com/news/

  The job should identify recent relevant articles or updates and collect available information such as:

  - article title
  - organization/source
  - publication date, when available
  - source URL
  - relevant article text or description

  The final research digest should present the most relevant items in a concise format for a graduate student studying agentic engineering.

  For each selected item, include:

  - Title
  - Source
  - Publication date, when available
  - URL
  - Concise summary
  - Why it matters

  The job must also preserve observable evidence from each execution so that a human can inspect what actually happened.

  The implementation should be repeatable and runnable locally.

  ------

  ## Context

  This task is part of Studio01: Delegation & the First Observable Run.

  The purpose is to practice delegating a bounded engineering task to a coding agent while maintaining:

  - clear task scope
  - observable execution
  - explicit success criteria
  - human verification
  - controlled failure handling
  - evidence-led correction

  The intended reader of the generated digest is a graduate student interested in:

  - agentic systems
  - AI agents
  - coding agents
  - LLM applications
  - tool use
  - model capabilities
  - AI infrastructure
  - AI safety and reliability
  - relevant AI engineering developments

  Prioritize technically meaningful information over marketing language.

  All files created or modified for this assignment must remain inside:

  ```
  studio/tcyxox/
  ```

  A suitable directory structure is:

  ```text
  studio/tcyxox/
  ├── delegation-card.md
  ├── code/
  ├── outputs/
  └── explanation-tcyxox.md
  ```

  The exact internal organization of `code/` and `outputs/` may differ if a simpler structure is appropriate.

  Each execution should preserve enough evidence for a human reviewer to determine:

  - which sources were attempted
  - which sources succeeded
  - which sources failed
  - how many items were discovered
  - what items were selected
  - what output was generated
  - what errors or warnings occurred
  - whether the run completed successfully, partially, or failed

  The implementation should support a controlled experiment in which one condition is deliberately changed after a baseline run.

  For example, one source may temporarily be changed to an invalid or unavailable URL in order to observe how the job responds.

  ------

  ## Success criteria

  A successful implementation must satisfy the following observable checks.

  1. The job can be run locally using a clearly documented command.
  2. The job attempts to access the configured official Anthropic and OpenAI sources.
  3. The status of each attempted source is observable.
  4. A normal run produces a Markdown research digest containing useful recent AI updates.
  5. Each selected item contains, when available:
     - title
     - source
     - publication date
     - URL
     - concise summary
     - why it matters
  6. The system does not invent unavailable article contents, dates, URLs, or other factual information.
  7. Each run preserves observable execution evidence, including at minimum:
     - run identifier or timestamp
     - sources attempted
     - source success/failure
     - number of items discovered
     - errors or warnings
     - output file path
     - final run status
  8. The final run status clearly distinguishes successful execution from partial or failed execution. Appropriate statuses may include:
     - `SUCCESS`
     - `DEGRADED`
     - `FAILED`
  9. A failure of one source must not be silently ignored or falsely reported as complete success.
  10. A controlled condition-change experiment is performed after the initial baseline run.
  11. Evidence from the baseline run and the changed-condition run is preserved separately.
  12. The observed failure is inspected before a correction is made.
  13. The correction is based on the observed evidence rather than unrelated changes.
  14. After the correction, the relevant condition is tested again and the new result is preserved for comparison.
  15. Previous run evidence must not be overwritten.
  16. Before claiming completion, the coding agent must perform a fresh run and verify the relevant success criteria against actual outputs and execution evidence.

  ------

  ## Restrictions

  All implementation work and generated artifacts must remain inside:

  ```
  studio/tcyxox/
  ```

  Do not modify:

  - shared files directly under `studio/`
  - another student's folder
  - unrelated repository files
  - repository configuration outside my assignment folder

  Do not create a `Studio01`, `studio01`, or `studio-01` subfolder.

  Do not create, write, rewrite, edit, or generate content for:

  ```
  studio/tcyxox/explanation-tcyxox.md
  ```

  That file must be written personally by the student without AI-generated text.

  Only use the explicitly configured public sources for the Research Update unless a human explicitly changes the scope.

  Do not:

  - bypass authentication
  - bypass authorization or permission boundaries
  - bypass paywalls or access restrictions
  - attempt to defeat anti-bot protections
  - access private information
  - modify external systems

  If access to a source is denied or unavailable, record the failure explicitly.

  Do not fabricate:

  - article content
  - article metadata
  - successful requests
  - execution logs
  - traces
  - test results
  - verification results

  All claimed execution results must come from an actual run.

  Do not commit or expose:

  - API keys
  - passwords
  - access tokens
  - session cookies
  - private credentials
  - private personal information

  If an API key is used, it must be supplied through an environment variable or equivalent local secret mechanism and must never appear in committed files.

  A failure of one source should produce either:

  - a controlled partial result with an explicit degraded status, or
  - a responsible stop if continuing would make the result unreliable.

  Do not report full success when required checks have failed.

  Preserve baseline, failure, and corrected run evidence separately.

  Prefer the simplest implementation that satisfies the task, observability, verification, and failure-handling requirements.

  Do not add unnecessary infrastructure such as a web interface, database, deployment system, or complex framework unless it is required by the task.
