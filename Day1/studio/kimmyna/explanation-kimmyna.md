<what the agents did> - Claude
- First the agent reads a PDF slide from lectures and extracts main and sub 
keywords and writes it down with the page numbers. 
- Using the keywords, the agent explains the concept but records the page or the 
source that it used to explain.
- It has an addition function for the users to explain the concepts to check
if one truly understood. 

<human decisions and why they were made>
- Instead of a quiz, I chose to use a teach back method where the user has to 
use their own words to explain to several questions about the main key word.
This is because, if you have explained the concepts with your own words, it 
means that you really understood what it means, not just memorizing words.
- the test/cheatsheets are provided when asked.
- The first slide sample I used was photo centered so the model couldn't really
retrieve information. The second sample was mostly words.


<how results were verified>
- check_summary.py checks if all the keywords were included, and the sources
are well noted.
- spot_check_auto.py checks if the tagged content([p.N]) are actually on the 
page.
- Before,the user had to open the PDF and compare and check but it was too
burdensome so I automated it. 

<uncertainties>
- Although I wrote use Sonnet for the model in the Restrictions part, it was ran
on Opus 5.
- While brainstorming, me and an AI agent thought 8 key core words are good per
slides as it's not too much or little to include the "important" "main" key 
words, however after running it through multiple slides, I've noticed how some
key words are missing and some are not important. Fixing the number for main 
key words was initially to set a standard for the AI not to overuse main key
words and also not to overuse sub key words. However, this part still needs 
improvement.
- AI checks AI's work for flaws( added b/c too burdensome for users) - may not 
be able to catch hallucinations.


