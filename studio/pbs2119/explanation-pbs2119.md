# Studio01 Explanation — pbs2119

Job: Research Update · Date: 2026-09-11

## What the agent did

I delegated the agent with scanning a list of preapproved websites for news on the AI industry and creating a summary document of recent news articles.  

In the agent's first run, it attempted to use the WebFetch tool to retrieve the web index for Anthropic's news and engineering announcement web pages as well as OpenAI's news webpage.  While the agent successfully pulled news from Anthropic, it exhausted the budget of allowable fetches in the delegation card before it could successfully pull any OpenAI articles.  

In run 2, the agent was asked to do the same news run, but was asked to reduce the viable window of news from 14 days to 3.  As a result, only 1 Anthropic news story was included and 6 OpenAI stories were included now that there was budget in the allowable fetches for pulling OpenAI news.  

In run 3, the agent was asked to do the same news run, but the trailing 3-day window for stories was cut to only include news from the same day as the run.  As a result, only one news story from OpenAI was included, which failed the condition that 3-8 news stories must be included for the run to be considered a success. 

In run 4, with a corrected date window (7 days) and updated minimum success number (1 article), the agent ran a successful new retrieval.  Now, 7 news items were retrieved as compared to the 1 from run three.

## Human decisions and why

I chose to do the news updates since I better understood how to accomplish the goal.  I did not understand at the time of the lab if the materials for the course were available, thus making summarizing them difficult to do.  

Initially I attempted to write the delegation card myself.  Claude Code reviewed it for me, and made it clear my criteria for success and allowable tools were far too vague.  It suggested specific tool names the agent could use after I prompted it for them, which I then guided the agent to incorporate.  It also suggested specific configurations and success criteria for a run, which I again accepted.

Two perturbations were chosen. The first was to lower the window of eligible stories to the last three days.  However, this did not actually result in a failed run.  So, the window was lowered again to be only news from the same day as the run.  This was chosen because prior runs made it clear not enough stories would be eligible to satisfy the success criteria that 3 to 8 stories must be included in the summary.  

To correct the weakness this perturbation exposed, the agent was guided to broaden the window for the search to the trailing seven days.  This would align the agent with the goal of creating a summary of news for the prior week.  Another improvement was to lower the success condition for minimum number of news stories in the summary file to 1.  

## How results were verified

I personally was able to check for a successful run by manually validating the success criteria, which was purposely kept simple.  This included seeing the output file exists in the correct locations, reviewing the file and confirming the number of entries were within the correct range, the publish dates were in the correct range, all listed URLs were real, and others.   

While the agent did make a checklist denoting which of the success criteria had been met, it did not always explain how exactly it validated them.  It did sometimes list bash commands in later runs that were used for verifying some criteria, but such citations were inconsistent and uncommon. 


## Uncertainties

During the runs, several curious observations arose.  On the first run, the 10 fetch limit prevented the agent from successfully retrieving OpenAI news that was eligible to be included.  The delegation card did not clarify whether leaving out news that should have been included was an error.

Also, after the first run, the agent (Claude Code) learned that a tool call that was effective for pulling a web index from Anthropic sites did not work for OpenAI sites.  So, its method of retrieving information from OpenAI sites was changed for all subsequent runs.  The expected role of 'memory' from run to run was not clarified.

While the summaries appeared valid during a surface inspection, to confirm the agent relayed a faithful representation of the story requires a deep inspection of the source file.  I did not perform such a deep inspection.  

Also, although the agent created a log of its actions, it was a higher-level summary and agent-created log as compared to something like a harness trace.  So, we are trusting that the agent faithfully represented the actions it took during a run. 
