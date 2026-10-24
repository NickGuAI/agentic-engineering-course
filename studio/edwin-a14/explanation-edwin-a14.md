# Studio 01 Run Explanation — Edwin Argudo (eaa2193)

## What the Agent did

The agent went and created the report I asked it for, as specified by the conditions of the delegation-card. It also took the liberty of writing code to make parsing of the information from the blog websites easier, as one of my requirements was that it collect terminology used in these posts, and sort them by occurence. 
## Human decisions

I added guardrails to keep it from straying from unauthorized internet searches to keep the agent focused on the task at hand. For the changed condition, I misspelled the word 'engineering' in the anthropic news url, and the agent handled this by correctly noting the failure and not proceeding to explore the anthropic website on its own, which was part of my restrictions. 


## Result Verification

I verified results by examining the output report the agent created as well as the trace of calls it made while making the report. The agent also self-validated, unprompted, by comparing its results to the criteria I had given it. 

## Uncertainties

Because I cannot validate the information provided by the report without reading the posts myself, the information itself is an uncertainty. 