I changed the missing input condition by removing the course materials from the prompt and permission boundary condition by removing the rule that prohibited invented lecture topic.

I verified the results by comparing the outputs from the changed prompt to agents. And since it is a single run comparison, so the results can vary across different runs.

For both tests, the original version tied to the actual course notes. However, after the changes, the model outputs some context that not actually supported by the notes.

For the missing permission boundary case, this is because the model does not have a restriction on using unsupported claims.
For the missing input case, this is because the model miss the necessary materials and start to guess.
