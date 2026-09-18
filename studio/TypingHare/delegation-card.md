# Delegation Card

## Task

> What specific artifact or result are you delegating to the AI?

Create a concise digest of three recent posts from OpenAI News. The posts should have been published between one and two weeks ago.

## Context

> What relevant inputs, files, tools, target audience, or learning preferences should the AI consider?

You should write a Python script using the **Tavily** library to scrape news from [OpenAI News](https://openai.com/news/). Pick three important news stories and write a gist of each one. Then, use Tavily to scrape Reddit, Quora, and X to collect people’s opinions about these stories. Pick some representative opinions and summarize them.

The target audience includes me and other students studying agentic engineering.

## Success criteria

> What is the observable check or metric that defines a successful run?

- Output a `digest.md` file in `studio/TypingHare/outputs/` containing a digest of three recent posts.
- Below each post, include its metadata: a link to the webpage, the publication date, and the author (if present).
- Below the metadata, summarize public opinions about the news, if you find any. You may quote some representative comments. Make sure to include a link to the source webpage for each quote.

## Restrictions

> Are there any prohibited actions, resource limits, or human approval boundaries to enforce?

- You must scrape webpages from the specified websites. Ignore toxic or unreasonable comments on social media.
- Ask for my approval before installing packages, using paid or API-based services, or accessing accounts or credentials.
- Do not modify any files outside `studio/TypingHare/`.
- Store all scripts and configuration files in `studio/TypingHare/code/`.
