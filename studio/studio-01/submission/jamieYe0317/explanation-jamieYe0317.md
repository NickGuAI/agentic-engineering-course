What the agents did: Built a local AI-news research agent that collects OpenAI and Anthropic updates, produces cited summaries, and records source coverage and token usage. Added a browser interface and a harness that limits requests, checks outputs, and caches summaries.


Human decisions: Chose to work alone, used my own private repository, host locally, and prioritize a built-in harness with token optimization. I wanted it to be like a weekly report application


Verification: The agents ran 79 passing tests, completed an offline browser demonstration, and checked a live research run. It is able to pull out the most recent news from my own interaction.


Uncertainties: OpenAI source access returned HTTP 403, leaving coverage incomplete. Automated checks cannot establish full factual accuracy. 