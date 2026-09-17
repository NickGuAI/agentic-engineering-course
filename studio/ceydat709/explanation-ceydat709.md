# Explanation

## What did the agent do?
Through a delegation card, I asked the agent to go through three different news pages and build a Markdown file based on the three most recent posts from each. It then wrote a Python script to check the output against the success criteria, which I specified in the delegation card.

## Human decisions and why
I decided to keep the markdown capped at 3 posts per source instead of pulling more because I wanted to keep the overall page digestible. I even specified that I didn't want dense bullet points on the page. I think this would also make it more skimmable for my audience, who are students in this class. Also, I decided to implement a fallback. I honestly have not read much of Anthropic Engineering news before, so I'm not even sure how often they upload. So, I had to decide what would happen if there turned out to be nothing posted in the current week. I decided that there would be a fallback where I use the 3 most recent posts instead of completely failing the run. Some information is better than none. I also chose not to let the agent use WebSearch, only WebFetch on the 3 URLs in the context. I did this because I didn't want it substituting in similar articles it found somewhere else.

## How results were verified
I verified the results by running validate.py, which checks the post counts, the bullet counts, duplicate links, and file length. I also actually went into the markdown file and fully read it myself to ensure that the links were all real posts and not ones that the agent potentially hallucinated.

## Any uncertainties
I realized the agent created an md file called 17-09-2026-change-explain.log, which I thought was a bit weird. The agent created this supporting file on its own initiative, and it wasn't something that was explicitly requested. So, I tried to decide whether that was helpful documentation. Additionally, I technically didn't read the actual posts, so I can't verify that the bullet points are accurate, which leaves an uncertainty.
