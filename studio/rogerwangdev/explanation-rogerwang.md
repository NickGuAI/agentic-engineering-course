# Explanation

I worked on a weekly AI news digest idea. The goal was to have an agent check Anthropic News, Anthropic Engineering, and OpenAI News, then summarize the most useful updates for someone studying Agentic Engineering.

One thing I noticed is that scraping websites is not perfectly clean. Some titles came with extra text or formatting issues, so the code had to clean and rank the results. This scraper will not stay reliable if the websites change their layout

For the changed condition, I looked at what would happen if part of the input was missing or if a permission boundary came up. One example was: what if one of the news sites could not be reached? In that case, the agent should not pretend everything worked. It should say which source failed, continue with the other sources, and mark the digest as partial.

Another boundary was scheduling. I wanted the task to run every Monday at 7:00 AM Eastern Time, but the agent should not actually create a real scheduled job unless I clearly approve it. So the sample run only describes the schedule and runs manually. I think this is a useful stop point because automatic actions can get messy if they happen without the user noticing.