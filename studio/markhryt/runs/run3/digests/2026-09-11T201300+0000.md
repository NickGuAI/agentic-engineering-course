# AI News Digest — 2026-09-11

_Generated 2026-09-11T20:13:00+00:00 · 20 new item(s) · method: extractive_

## Overview

20 new item(s): 10 from Anthropic News, 10 from Anthropic Engineering. Summaries are extractive (first sentences); no model was used.

## Anthropic News

### [Developing Enterprise Frontier Safeguards with our customers](https://www.anthropic.com/news/enterprise-frontier-safeguards)
_Developing Enterprise Frontier Safeguards with our customers · 2026-09-01_

Today we’re announcing Enterprise Frontier Safeguards (EFS), a solution that combines the privacy of zero data retention (ZDR) with state-of-the-art safeguards for detecting misuse. EFS works by storing data in cloud infrastructure controlled by the customer, not Anthropic.

### [Improving our alignment and security efforts](https://www.anthropic.com/news/improving-alignment-security-efforts)
_Improving our alignment and security efforts · 2026-08-31_

On July 30, we reported three incidents in which Claude models gained unauthorized access to real computer systems. The models—intentionally running without cyber safeguards for evaluation purposes—accessed the internet due to a misconfiguration inside a third-party evaluation environment.

### [Previewing the Model Hardware Standard](https://www.anthropic.com/news/model-hardware-standard-research-preview)
_Previewing the Model Hardware Standard · 2026-08-27_

We’re opening a research preview of the Model Hardware Standard (MHS), a shared specification for AI agents to safely operate physical devices, to a first group of scientific research labs and advanced manufacturers. MHS enables AI agents to operate multiple lab and manufacturing instruments, such as microscopes, liquid handlers, and robotic arms, in parallel, and perform intricate tasks ranging…

### [Expanding our support for scientists](https://www.anthropic.com/news/expanding-support-for-scientists)
_Expanding our support for scientists · 2026-08-27_

As Claude becomes increasingly capable at scientific research, we are focusing on building products and programs to support the research community. In June, we launched Claude Science, a product that integrates the tools that researchers most commonly use, produces auditable artifacts, and provides flexible access to computing resources.

### [Funding better evaluations of AI’s impact on wellbeing](https://www.anthropic.com/news/wellbeing-research-grants)
_Funding better evaluations of AI’s impact on wellbeing · 2026-08-25_

We’re launching a $5 million grant program to fund independent research into how AI impacts users’ wellbeing. The program will provide direct funding, access to our models, and technical support to grantees building open-source evaluations that help the AI industry measure how our models affect those who use them.

### [How Claude’s text watermark works](https://www.anthropic.com/news/claude-text-watermark)
_How Claude’s text watermark works · 2026-08-14_

Future Claude models will generate text that contains a watermark. This is a way of determining the likelihood that Claude was involved in writing the text, and we, along with several other major AI providers, are implementing this change to comply with the EU AI Act.

### [Improving Fable 5's biology safeguards](https://www.anthropic.com/news/improving-fable-5-s-biology-safeguards)
_Improving Fable 5's biology safeguards · 2026-08-07_

We’re making updates to Claude Fable 5’s biology safeguards in a way that substantially reduces false positives. Fable 5 users will now experience many fewer “fallbacks”—where the system switches to a less capable model after they make a biology-related query.

### [Mariano-Florentino (Tino) Cuéllar to join Anthropic as Chief Global Affairs Officer](https://www.anthropic.com/news/tino-cuellar)
_Mariano-Florentino (Tino) Cuéllar to join Anthropic as Chief Global Affairs Officer · 2026-08-04_

Mariano-Florentino (Tino) Cuéllar will join Anthropic as its first Chief Global Affairs Officer, leading the company’s work on policy, strategic international engagement, and government relationships worldwide. Tino’s career spans law, technology, international security, and public institutions at the international, national, and state levels.

### [Investigating three real-world incidents in our cybersecurity evaluations](https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals)
_Investigating three real-world incidents in our cybersecurity evaluations · 2026-07-30_

In a review of our cybersecurity evaluation transcripts, we found three incidents in which a Claude model reached the internet from within or while interacting with a third-party evaluation environment, and then gained unauthorized access to the real systems of three different organizations. Below we describe what happened, how it happened, and what we’re changing.

### [Our position on open-weights models](https://www.anthropic.com/news/position-open-weights-models)
_Our position on open-weights models · 2026-07-27_

A post by Dario Amodei, Anthropic CEO Over the last few days there has been a lot of discussion about open-weights models, especially those from China. Reports suggest that some US officials are considering banning the use of Chinese open-weights models by US companies.

## Anthropic Engineering

### [How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude)
_How we contain Claude across products · 2026-05-25_

Twelve months ago, we'd have rejected out of hand the idea of granting Claude access sufficient to take down an internal Anthropic service. Today that level of access is routine, and Anthropic developers are more productive for it.

### [An update on recent Claude Code quality reports](https://www.anthropic.com/engineering/april-23-postmortem)
_An update on recent Claude Code quality reports · 2026-04-23_

Over the past month, we’ve been looking into reports that Claude’s responses have worsened for some users. We’ve traced these reports to three separate changes that affected Claude Code, the Claude Agent SDK, and Claude Cowork.

### [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)
_Scaling Managed Agents: Decoupling the brain from the hands · 2026-04-08_

Get started with Claude Managed Agents by following our docs. A running topic on the Engineering Blog is how to build effective agents and design harnesses for long-running work.

### [How we built Claude Code auto mode: a safer way to skip permissions](https://www.anthropic.com/engineering/claude-code-auto-mode)
_How we built Claude Code auto mode: a safer way to skip permissions · 2026-03-25_

By default, Claude Code asks users for approval before running commands or modifying files. This keeps users safe, but it also means a lot of clicking "approve." Over time that leads to approval fatigue, where people stop paying close attention to what they're approving.

### [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
_Harness design for long-running application development · 2026-03-24_

Written by Prithvi Rajasekaran, a member of our Labs team. Over the past several months I’ve been working on two interconnected problems: getting Claude to produce high-quality frontend designs, and getting it to build complete applications without human intervention.

### [Eval awareness in Claude Opus 4.6’s BrowseComp performance](https://www.anthropic.com/engineering/eval-awareness-browsecomp)
_Eval awareness in Claude Opus 4.6’s BrowseComp performance · 2026-03-06_

BrowseComp is an evaluation designed to test how well models can find hard-to-locate information on the web. Like many benchmarks, it is vulnerable to contamination: answers leak onto the public web through academic papers, blog posts, and GitHub issues, and a model running the eval can encounter them in search results.

### [Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise)
_Quantifying infrastructure noise in agentic coding evals · 2026-02-05_

Agentic coding benchmarks like SWE-bench and Terminal-Bench are commonly used to compare the software engineering capabilities of frontier models—with top spots on leaderboards often separated by just a few percentage points. These scores are often treated as precise measurements of relative model capability and increasingly inform decisions about which models to deploy.

### [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler)
_Building a C compiler with a team of parallel Claudes · 2026-02-05_

Written by Nicholas Carlini, a researcher on our Safeguards team. I've been experimenting with a new approach to supervising language models that we’re calling "agent teams." With agent teams, multiple Claude instances work in parallel on a shared codebase without active human intervention.

### [Designing AI-resistant technical evaluations](https://www.anthropic.com/engineering/AI-resistant-technical-evaluations)
_Designing AI-resistant technical evaluations · 2026-01-21_

Written by Tristan Hume, a lead on Anthropic's performance optimization team. Tristan designed—and redesigned—the take-home test that's helped Anthropic hire dozens of performance engineers.

### [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
_Demystifying evals for AI agents · 2026-01-09_

Introduction Good evaluations help teams ship AI agents more confidently. Without them, it’s easy to get stuck in reactive loops—catching issues only in production, where fixing one failure creates others.
