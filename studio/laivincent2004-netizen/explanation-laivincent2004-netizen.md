# Studio 01 Explanation

Codex created a bounded OpenAI News agent in `code/openai_news_agent.py` and ran it for the delegation card task. The normal run used the official OpenAI News RSS feed, selected the three latest posts, preserved source links, wrote a beginner-friendly summary, and recorded the run in `output/openai-news-run-record.md`.

For the changed-condition run, I asked the agent to simulate one required source item being unavailable. Instead of guessing or reusing prior details, the agent stopped, explained which evidence was missing, and wrote a separate stop artifact plus run record. The main change was that the first run completed the summary, while the second run showed a responsible stop when the evidence boundary was violated.

Human decision was made just before the AI started working. I wrote the requirements in the delegation card. I also had to check if the results align with the plan, and had to tell the model to modify the agent code when it was not satisfactory.

Verification: The model wrote "test_openai_news_agent.py" to test if the agent properly ran and created output.

Uncertainties: The first agent that the model built would ignore the "--unavailable-url" requirement in "python openai_news_agent.py --unavailable-url "https://openai.com/index/cooley-gopublic/"", which asks it to pretend that the following url could not be accessed and write an "unavailable report" telling the user that it cannot access the url. I had to ask the model to change it a few times for it to work.
