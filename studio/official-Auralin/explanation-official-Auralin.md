# Explanation of work
I decided to write an AI news research agent. I liked the structure of the assignment and it felt more verifiable. 

## A brief summary of what the agents did
The agent began by cloning the repo and making the approproriate directory. I prompted it to plan without execution. After reviewing and prompting the agent created logic for collecting publications. The model lists it's main implementation decision as "separating predictable operations from language-model judgement." The model made a Python script to handle fetching, dates, duplicate dection, file writing, and validation. Then an agent handles the summarization process.  The agent's run does the following:
* Reads the two Anthropic sites, and OpenAI's official RSS feed (because the website was giving a 403 error), and then retrieves the text of the articles.
* Compares URLs to saved URLs to identify duplicates. It performs additional hashes and fingerprints to identify any changes.
* Prompts the Codex CLI agent with the collected text and instructions to sumarize.
* Validates that there is exactly one response per URL and checks quotes for accuracy.
* Publishes the summaries to a dated md file in ../outputs/live/reports

## Human decisions and why they were made
I decided to plan together before allowing the agent to create anything. 
I told the agent the exact directory location I wanted to use including my github username. 
I decided to limit the agent's new sources to the three listed in the assignment slide, but then later decided to allow the OpenAI RSS feed as a fallback. 
I decided I explicitly wanted to run somthing locally which I could inspect, run, and modify on my own computer. 
After the agent suggested running 9AM Eastern on weekdays, I decided that was a reasonable schedule and approved. 
The agent initially suggested a different directory structure, I told it to follow exactly your proposed structure. 
The agent initially made a single output file for errors and summaries, I decided that a dated file was better because it created a paper trail and prevented overwritten summaries. I additionally decided that errors should be kept in log files. 

## How results were verified
The agent created verification tests and then I checked the outputs and gave feedback on necessary changes. The agent reported that its testing resulted in 21 passing tests. 
Additionally I read agent.py, run.py, and verify.py. 

## Any uncertainties
I would like more time to test the summarizations to see if it is consistent, but I'm fairly happy with the outcome, and feel like I have a decent understanding of what was created. 