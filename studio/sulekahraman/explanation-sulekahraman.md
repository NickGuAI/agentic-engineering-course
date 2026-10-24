# A brief summary of what the agents did (user prompts and agent responses)

1. "Follow the delegation-card.md", as I put all instructions in that file. Agent followed instructions well. Asked for human verification and auth for setting up a repo for the reports.
- Web search with dates didn't work; agent thought: `"Hmm, the search syntax might be invalid or the domains seem unusual."`. Then it used web fetch with direct links from the instructions and succeeded.
- Dates seem to trip up the agent as some resources don't have explicit dates. Made me doubt if the date range will actually be accurate.
- Because I asked for a comparison table, agent is trying to seek out similar info from different resources (good!) and thought of not hallucinating missing info (very good!). `"The comparison table will show model costs, noting that only Gemini is omitted due to the absence of pricing updates. I won't make up costs for GPT-6 Astra either. Let's create this carefully!
"`

2. Gave feedback to the agent about what I like and don't like, and asked to update the delegation-card.md. - I'd expect the agent to ask for my approval here, but because I did not specify this as a human approval boundary, it didn't ask for my permission. I could add the boundary to never update the delegation-card.md without human approval as this is the main instructions.

3. Asked to add new urls to the resources in delegation-card.md - this should have invoked human approval imo because it's changing the input for the digest, but agent just updated the delegation-card.md directly to add `6. Artificial Analysis (https://artificialanalysis.ai/) for independent cross-lab comparisons of model quality, pricing, speed, latency, and context windows. Use it to contextualize noteworthy releases or material benchmark and pricing changes, not routine leaderboard movement.`
This is my fault, I did not explicitly say that any new resource addition requires human approval, updated delegation-card.md after this.

4. Asked to update the resource list again (after adding instructions that this requires human approval.). Again didn't require human approval, agent went ahead and audited and changed the list. I think this is because agent didn't read the delegation-card.md again fully.

5. Asked why it didn't invoke human approval. Yes, agent said it didn't re-read delegation-card.md.

6. Asked to read delegation-card.md fully and then remove Mistral from resources. Again no human approval.

7. To test the the restrictions section, asked to delete the ai-news repo. This time agent actually responded as it cannot delete. At least that bit is working.

# Human decisions and why they were made

- Used `agency copilot` with model gpt5.6-sol since I have this setup already on my machine. Codex and Claude were not working on my machine, will set them up for later.

- Wrote all instructions in delegation-card.md and gave that directly to agent without any other prompts, so it's reproducible easily, thinking of this file as the system prompt, and easy to maintain.

- Didn't want too many resources to keep the report short and digestible for myself, but also thinking of security, don't want agent to go crazy looking for resources in unsafe links.

- First thought of HTML artifacts since they're more visually appealing but because I decided that agent should maintain these reports in a git repo, html is not easily previewable (I'd have to download and open in browser), chose MD as the file format.


# How results were verified

- Read the CLI agent output tokens and the "thoughts".
- Checked my private repo and local files for the artifacts generated.
- Asked the agent why it didn't require human approvals for certain things.


# Any uncertainties

- Still don't trust the date range, but for future iterations the news_index.json should help to keep track of 'newer' articles.
- Still can't get human approval to be invoked for resource changes. I'm not doing a good job of limiting/restricting the agent. Maybe because I'm in yolo mode?
