# Utilization of small LLMs for retrieval of structured information from documents

Recent developments in generative AI and Large Language Models (LLMs) have led to significant advancements in natural language understanding and generation. These models show remarkable capabilities in various language-related tasks, including text summarization, translation, question answering, and generating human-like text. One notable trend is the increasing interest of companies in using LLMs to query their own data. However, the best performing LLMs are typically very large, expensive to use, and/or require data to be sent to remote servers. The smaller LLMs, on the other hand, are free to use, can be fitted onto consumer hardware, can generate high-quality responses, but the output may not be structured or constrained in a desired way.

The focus of the current diploma work was to create a proof of concept for the structured extraction of information from text documents, such as scientific articles and patents, using relatively small local LLMs. Output constraining was tested with Guidance, Outlines, and LMQL libraries. Each library had strengths and weaknesses:

* Guidance: Reproducible, intuitive, flexible, and well-documented but complex to prompt.
* Outlines: Easy to prompt, integrated with Pydantic, and well-documented but unstable output.
* LMQL: Reproducible and simple to prompt but with limited constraint possibilities and limited maintenance.
  
All libraries were relatively slow and would require further prompt development. Additionally, further investigation is needed to optimize document chunking, determining which parts of the documents should be injected or how documents should be prepared prior to injection. For the final application, the inputs and outputs were structured using Pydantic, constrained with Guidance, and saved to an SQLite database.

This project was my own explorative work performed in parallel with my studies in tight collaboration with my supervisor (~4 weeks). It should be noted that the technologies evaluated are still very much under development, often with limited functionality, incomplete development, and inconsistent data upkeep, thus requiring a fair amount of experimentation.
