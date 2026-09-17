# Comprehension check: SUPPORTED / CONTRADICTED / NOT_FOUND -- results

**full**: model `openai/gpt-5.6-luna`, 551863 real input tokens (3 fresh + 0 cache-read + 551860 cache-write), cost $0.2776, wall time 10.51s, accuracy 16/20 (80%)
**excerpts**: model `openai/gpt-5.6-luna`, 3076 real input tokens (3 fresh + 0 cache-read + 3073 cache-write), cost $0.0019, wall time 9.22s

| id | doc | depth | kind | alteration | expected | label (full) | label (excerpts) | verdict | justification (full) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 4203 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Mei’s Context Engineering survey notes that many surveys focus on specialized subfields, motivating a unified taxonomy. |
| 2 | 1 | 12756 | claim | number | CONTRADICTED | CONTRADICTED | CONTRADICTED | correct | Mei’s survey states that PoSE extends context to 128K tokens, not 256K. |
| 3 | 1 | 8164 | reference | none | NOT_FOUND | SUPPORTED | NOT_FOUND | wrong at full -- correct with excerpts only (length-attributable) | Mei defines context engineering as dynamically retrieving, selecting, formatting, and assembling contextual components. |
| 4 | 2 | 140720 | claim | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Liu et al.’s Lost in the Middle shows substantial performance changes based on the position of relevant information. |
| 5 | 3 | 159575 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | MemGPT distinguishes main context, available during inference, from external context stored outside the fixed context window. |
| 6 | 4 | 173669 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Zhang et al.’s ACE identifies context collapse as a failure mode of repeatedly rewriting accumulated context. |
| 7 | 4 | 171852 | reference | entity | CONTRADICTED | NOT_FOUND | CONTRADICTED | wrong at full -- correct with excerpts only (length-attributable) | The documents do not establish that DSPy itself regularly defeats strong reference models across both agentic and specialized tasks. |
| 8 | 5 | 200027 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Hsieh et al.’s RULER includes retrieval, multi-hop tracing, aggregation, and question-answering tasks using controllable synthetic contexts. |
| 9 | 5 | 199261 | claim | number | CONTRADICTED | CONTRADICTED | CONTRADICTED | correct | RULER evaluates 17 models across 13 representative task configurations, not eight assessment scenarios. |
| 10 | 6 | 228409 | claim | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Wu et al.’s LongMemEval reports approximately a 30% accuracy drop for commercial assistants and long-context models on sustained-interaction memory. |
| 11 | 6 | 228692 | reference | none | NOT_FOUND | NOT_FOUND | NOT_FOUND | correct | The documents do not report substantially higher retention from assistants that proactively prompt users about private history. |
| 12 | 7 | 256179 | claim | negation | CONTRADICTED | CONTRADICTED | CONTRADICTED | correct | Yao et al.’s ReAct reports improvements over imitation and reinforcement-learning methods on ALFWorld and WebShop. |
| 13 | 8 | 293064 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Lewis et al.’s RAG paper describes Jeopardy generation as requiring precise, factual, and specific clues about target entities. |
| 14 | 9 | 316169 | claim | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | Park et al.’s Generative Agents architecture combines recency, importance, and relevance to retrieve memories for the current situation. |
| 15 | 10 | 339462 | claim | scope | CONTRADICTED | CONTRADICTED | CONTRADICTED | correct | Hsieh et al.’s RULER discussion reports BABILong’s counting task at 28% even at 0K context, not only with extensive distractors. |
| 16 | 11 | 358454 | reference | attribution | CONTRADICTED | NOT_FOUND | CONTRADICTED | wrong at full -- correct with excerpts only (length-attributable) | Mem0 proposes its own graph-enhanced variant in the same paper; the documents do not identify a separate paper making that proposal. |
| 17 | 12 | 374155 | claim | entity | CONTRADICTED | CONTRADICTED | CONTRADICTED | correct | Brown et al.’s GPT-3 paper, not a BERT paper, reports prompting without parameter updates and evaluates language, reasoning, and mathematical tasks. |
| 18 | 12 | 381780 | reference | none | NOT_FOUND | CONTRADICTED | NOT_FOUND | wrong at full -- correct with excerpts only (length-attributable) | Brown et al. discuss scaling performance with model size and compute; the relationship is not attributed entirely to learning-rate and batch-size optimization. |
| 19 | 13 | 444939 | definition | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | The Gemini 1.5 report states that Flash achieves nearly perfect retrieval across text, video, and audio up to approximately 2M tokens. |
| 20 | 13 | 437678 | claim | none | SUPPORTED | SUPPORTED | SUPPORTED | correct | The Gemini 1.5 report describes over 99% retrieval up to 10M tokens and characterizes this as a major advance over Claude 3 and GPT-4 Turbo context capabilities. |

'verdict' compares the full-context label to the expected label. A miss at full length that the model gets right with only the 20 excerpts is called out explicitly, since that means the paraphrase itself was not the problem -- length was.

## All 20 statements

1. [SUPPORTED] Due to the swift advancement of LLMs, numerous overview papers have emerged, though they primarily concentrate on narrow subfields rather than the wider scope of Context Engineering.
2. [CONTRADICTED] Position Sequence Tuning scales input length limits to a maximum of 256K tokens by integrating a variety of positional interpolation methods.
3. [NOT_FOUND] Unlike prompt engineering, which relies primarily on manual instructions, context engineering utilizes algorithmic pipelines to dynamically select and format input data for large language models.
4. [SUPPORTED] The accuracy of modern language models on multi-document question answering and key-value retrieval shifts substantially based on where the crucial data is located in the input.
5. [SUPPORTED] Data residing in the main context is available for immediate retrieval during model processing, while external context comprises data positioned beyond this defined boundary.
6. [SUPPORTED] During sequential system adjustments, a language model that completely regenerates its gathered background information risks experiencing context collapse, which severely degrades its final results.
7. [CONTRADICTED] The innovative methodology called DSPy regularly defeats robust reference models on both autonomous agent and highly specialized problem sets.
8. [SUPPORTED] RULER incorporates various evaluation categories extending past simple search operations, using machine-produced material to diminish dependence on parametric knowledge while enabling regulation of text spans and difficulty levels.
9. [CONTRADICTED] Researchers assessed seventeen long-context systems utilizing eight distinct assessment scenarios within the RULER framework to measure capabilities beyond standard information retrieval.
10. [SUPPORTED] When tested on LongMemEval, proprietary chatbots and extended-context language models exhibit a 30% performance reduction when recalling facts over extended dialogues.
11. [NOT_FOUND] Recent investigations indicate that digital companions which actively prompt individuals about their private history achieve substantially higher user retention scores over extended periods.
12. [CONTRADICTED] On the ALFWorld and WebShop benchmarks, the ReAct approach is unable to demonstrate superior performance compared to reinforcement and imitation learning methodologies.
13. [SUPPORTED] Formulating Jeopardy prompts from their target subjects is a demanding and information-heavy creative endeavor since the resulting clues must serve as highly specific and accurate assertions.
14. [SUPPORTED] To shape how a language model reacts to a current scenario, choosing a portion of perceived events relies on a trio of key elements operating in tandem to generate successful outcomes.
15. [CONTRADICTED] Within the BABILong evaluation, the counting task struggles significantly, obtaining twenty-eight percent accuracy, only when surrounded by extensive distracting context.
16. [CONTRADICTED] Mem0 (2025) designs an adaptable framework for organizing dialogue data, but a different paper proposed its upgraded version using graph structures to map intricate connections between concepts.
17. [CONTRADICTED] BERT exhibits robust capabilities across numerous linguistic evaluations and mathematical exercises solely through conversational prompts, bypassing parameter adjustments.
18. [NOT_FOUND] The power-law relationship between compute and language model quality is entirely driven by the optimization of hyperparameters like learning rate and batch size.
19. [SUPPORTED] When handling inputs spanning two million tokens, Gemini 1.5 Flash demonstrates nearly complete retrieval accuracy for auditory, written, and visual formats.
20. [SUPPORTED] Reaching a capacity of ten million tokens, Gemini 1.5 exhibits extremely precise information retrieval in multiple formats, representing a massive advancement over Claude 3.0 and GPT-4 Turbo.
