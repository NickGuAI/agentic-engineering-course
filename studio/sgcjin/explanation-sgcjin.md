# Explanation

## What the agent did

The agent takes the prompt like "Read the delegation card and Digest the lecture 1 in <https://courseworks2.columbia.edu/courses/251673/files> for me" and then downloads and reads the related resources according to the given uris. After that, it will produce a html file as a digested study guide. After the whole process, it saves the run report as well as the html file under the `outputs` directory.

## Decisions

First, I made the decision to ask codex to download the course materials from urls instead of asking me to download them manually. This is because I want to eliminate the interactions during the whole process. However, this caused some failures in downloading the pdf files. When codex encountered this issue, it skipped the downloading process, instead, it used the browser use tool to read texts rendered on the webpage, which is not acceptable as it didn't read the full content. Therefore, I decided to add restrictions that downloading pdfs from courseworks file page is required, and try actual mouse clicks rather than browser use tool because I observed that clicking the files download control worked after the earlier download attempt failed.

Second, I changed the input condition by providing ambiguous urls such as `[https://courseworks2.columbia.edu/courses/``251673``/files](https://courseworks2.columbia.edu/courses/``234152``/files)`. The displayed course id is
251673 but the actual course id in the link is 234152.  Codex then proceed to process the former course without checking with me. Therefore, after this run, I decided to add another restriction: if my input is ambiguous, it should pause and pause for my confirmation.

## Verification
I verified the first decision by inputting the course file uri it failed to download before, and checking the run log under the outputs directory. When Codex found that it could not download the PDF files, it tried to use the Mouse clicks and correctly read the PDF files using the PDF reading tool. I also compared the content in the study guide HTML it produced with the actual file content. The result shows that it successfully made use of the lecture resources. 
Then I verified the second decision by opening another chat session and inputting the same ambiguous URLs. From its responses, Codex can follow the restrictions and pause to confirm which course will be used to generate the study guide (Lecture 4 studyguide).

## What remains uncertain
What remains uncertain is whether the downloading process works for other types of files, like PPTX. Other courses may use different file types than the course I used to test. Also, some of the course materials might be redirected to other web pages. Therefore, the ability to handle other file types using this delegation card remains uncertain.