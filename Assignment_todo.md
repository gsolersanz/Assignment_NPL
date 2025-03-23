In this practice, you will apply the knowledge acquired in Session 2 (language understanding) and Session 3 (language generation) of this course.

The objective is to develop an automatic summarization system that combines information extraction techniques (language understanding) with generative text models (language generation). Given a corpus of documents in PDF format, this system will extract structured information from the documents and generate an abstractive summary using a generative language model. The summary should concisely describe all the relevant information for users.

Specifically, this project will focus on extracting information about scholarships for students published in the Boletín Oficial del Estado (BOE). A compressed file containing a set of five PDFs related to scholarship announcements for students from the 2020-2021 academic year to the 2024-2025 academic year is available in Moodle under this session ("Corpus practical assignment 1"). This will serve as your working corpus. The five provided PDFs have a very similar format and contain the same type of information, but it is essential to demonstrate that your solution works across all of them.

From this dataset, you must decide what type of information to extract: 

Which educational programs do the scholarships apply to? 
What are the scholarship amounts based on academic performance? 
What are the income thresholds? 
What are the application deadlines? It's up to you! 


The more information your system can extract, the better. This extracted information should be saved in a file in JSON, CSV, or XML format (whichever you prefer). Based on this file, you will generate the final abstractive summary.

Practice Details:

The project is group-based, and teams should consist of 3 to 6 members.
This assignment accounts for 30% of the final grade for the course.
The deadline for submission is Friday, April 4, at 11:59 PM.
The submission must include: a report in PDF format (no minimum or maximum page limit) and a public repository containing the developed code (e.g., GitHub, Kaggle notebook, etc.).
One group representative must upload the report on the activity's submission page.
Report Structure (with grading percentages):
Cover page: must include the project title and the names of all team members.
Introduction (5%): introduces the problem being addressed. Must include a link to the public repository containing the developed code.
Data (25%): describes the information extracted from the PDFs, including a link to the structured files (CSV, JSON, or XML) containing the extracted data. The amount and type of information extracted from each PDF will be considered when grading this section.
Architecture (25%): describes the system’s architecture, illustrating how the information extraction components interact with the automatic text generation components. A diagram should be included to visualize the components and interactions.
Evaluation (25%): primarily assesses testing with different language generation models. Evaluating the information extraction component (i.e., how many fields the system consistently extracts correctly from the proposed ones) is not mandatory but will be positively considered.
Conclusions (20%): discussion of the results and final conclusions of the study.