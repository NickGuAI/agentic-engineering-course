# Delegation Card

## Task
I'm delegating the research update - keeping up with the latest news and developments of AI by reading the top article on the OpenAI News section (https://openai.com/news/).

Run automatically every 24 hours after the initial immediate run and short follow-up run. The active recurring schedule is anchored at September 18, 2026, 02:29 UTC (September 17 at 10:29 p.m. Eastern daylight time).

## Context
The AI should consider the input website (https://openai.com/news/), use the tool of the internet to navigate to the first article, see me as the target audience (a computer science master's student), and take my learning preferences into account (I like detailed, hierarchical bullets, with no more than 50 words per bullet)

## Success criteria
Observable check is that the title of the first article is clearly displayed, and then a detailed hierarchical bullet summary is displayed underneath it.

Deliver each completed update in the existing conversation and save a fresh timestamped summary and execution trace in outputs/. Preserve all previous outputs. Perform and save the run even if the first article is unchanged, and clearly note that fact.

## Restrictions
There should not be more than 3 "levels" of bullets (one level is a deeper version of another level), there cannot be more than 10 bullets total, and each bullet must contain no more than 50 words.
