# #!/usr/bin/env python

# from __future__ import annotations

# import asyncio
# from datetime import datetime
# from typing import Any, Callable, Coroutine, Optional, Union

# from pydantic import TypeAdapter, model_validator

# from metagpt.actions import Action
# from metagpt.logs import logger
# from metagpt.tools.search_engine import SearchEngine
# from metagpt.tools.web_browser_engine import WebBrowserEngine
# from metagpt.utils.common import OutputParser
# from metagpt.utils.parse_html import WebPage
# from metagpt.utils.text import generate_prompt_chunk, reduce_message_length

# LANG_PROMPT = "Please respond in {language}."

# RESEARCH_BASE_SYSTEM = """You are an AI critical thinker research assistant. Your sole purpose is to write well \
# written, critically acclaimed, objective and structured reports on the given text."""

# RESEARCH_TOPIC_SYSTEM = "You are an AI researcher assistant, and your research topic is:\n#TOPIC#\n{topic}"

# SEARCH_TOPIC_PROMPT = """Please provide up to 2 necessary keywords related to your research topic for Google search. \
# Your response must be in JSON format, for example: ["keyword1", "keyword2"]."""

# SUMMARIZE_SEARCH_PROMPT = """### Requirements
# 1. The keywords related to your research topic and the search results are shown in the "Search Result Information" section.
# 2. Provide up to {decomposition_nums} queries related to your research topic base on the search results.
# 3. Please respond in the following JSON format: ["query1", "query2", "query3", ...].

# ### Search Result Information
# {search_results}
# """

# COLLECT_AND_RANKURLS_PROMPT = """### Topic
# {topic}
# ### Query
# {query}

# ### The online search results
# {results}

# ### Requirements
# Please remove irrelevant search results that are not related to the query or topic.
# If the query is time-sensitive or specifies a certain time frame, please also remove search results that are outdated or outside the specified time frame. Notice that the current time is {time_stamp}.
# Then, sort the remaining search results based on the link credibility. If two results have equal credibility, prioritize them based on the relevance.
# Provide the ranked results' indices in JSON format, like [0, 1, 3, 4, ...], without including other words.
# """

# WEB_BROWSE_AND_SUMMARIZE_PROMPT = """### Requirements
# 1. Utilize the text in the "Reference Information" section to respond to the question "{query}".
# 2. If the question cannot be directly answered using the text, but the text is related to the research topic, please provide \
# a comprehensive summary of the text.
# 3. If the text is entirely unrelated to the research topic, please reply with a simple text "Not relevant."
# 4. Include all relevant factual information, numbers, statistics, etc., if available.

# ### Reference Information
# {content}
# """


# CONDUCT_RESEARCH_PROMPT = """### Reference Information
# {content}

# ### Requirements
# Please provide a detailed research report in response to the following topic: "{topic}", using the information provided \
# above. The report must meet the following requirements:

# - Focus on directly addressing the chosen topic.
# - Ensure a well-structured and in-depth presentation, incorporating relevant facts and figures where available.
# - Present data and findings in an intuitive manner, utilizing feature comparative tables, if applicable.
# - The report should have a minimum word count of 2,000 and be formatted with Markdown syntax following APA style guidelines.
# - Include all source URLs in APA format at the end of the report.
# """


# class CollectLinks(Action):
#     """Action class to collect links from a search engine."""

#     name: str = "CollectLinks"
#     i_context: Optional[str] = None
#     desc: str = "Collect links from a search engine."
#     search_func: Optional[Any] = None
#     search_engine: Optional[SearchEngine] = None
#     rank_func: Optional[Callable[[list[str]], None]] = None

#     @model_validator(mode="after")
#     def validate_engine_and_run_func(self):
#         if self.search_engine is None:
#             self.search_engine = SearchEngine.from_search_config(self.config.search, proxy=self.config.proxy)
#         return self

#     async def run(
#         self,
#         topic: str,
#         decomposition_nums: int = 1, ####
#         url_per_query: int = 1,
#         system_text: str | None = None,
#     ) -> dict[str, list[str]]:
#         """Run the action to collect links.

#         Args:
#             topic: The research topic.
#             decomposition_nums: The number of search questions to generate.
#             url_per_query: The number of URLs to collect per search question.
#             system_text: The system text.

#         Returns:
#             A dictionary containing the search questions as keys and the collected URLs as values.
#         """
#         system_text = system_text if system_text else RESEARCH_TOPIC_SYSTEM.format(topic=topic)
#         keywords = await self._aask(SEARCH_TOPIC_PROMPT, [system_text])
#         try:
#             keywords = OutputParser.extract_struct(keywords, list)
#             keywords = TypeAdapter(list[str]).validate_python(keywords)
#         except Exception as e:
#             logger.exception(f"fail to get keywords related to the research topic '{topic}' for {e}")
#             keywords = [topic]
#         results = await asyncio.gather(*(self.search_engine.run(i, as_string=False) for i in keywords))

#         def gen_msg():
#             while True:
#                 search_results = "\n".join(
#                     f"#### Keyword: {i}\n Search Result: {j}\n" for (i, j) in zip(keywords, results)
#                 )
#                 prompt = SUMMARIZE_SEARCH_PROMPT.format(
#                     decomposition_nums=decomposition_nums, search_results=search_results
#                 )
#                 yield prompt
#                 remove = max(results, key=len)
#                 remove.pop()
#                 if len(remove) == 0:
#                     break

#         model_name = self.config.llm.model
#         prompt = reduce_message_length(gen_msg(), model_name, system_text, self.config.llm.max_token)
#         logger.debug(prompt)
#         queries = await self._aask(prompt, [system_text])
#         try:
#             queries = OutputParser.extract_struct(queries, list)
#             queries = TypeAdapter(list[str]).validate_python(queries)
#         except Exception as e:
#             logger.exception(f"fail to break down the research question due to {e}")
#             queries = keywords
#         ret = {}
#         for query in queries:
#             ret[query] = await self._search_and_rank_urls(topic, query, url_per_query)
#         return ret

#     async def _search_and_rank_urls(
#         self, topic: str, query: str, num_results: int = 4, max_num_results: int = None
#     ) -> list[str]:
#         """Search and rank URLs based on a query.

#         Args:
#             topic: The research topic.
#             query: The search query.
#             num_results: The number of URLs to collect.
#             max_num_results: The max number of URLs to collect.

#         Returns:
#             A list of ranked URLs.
#         """
#         max_results = max_num_results or max(num_results * 2, 6)
#         results = await self._search_urls(query, max_results=max_results)
#         if len(results) == 0:
#             return []
#         _results = "\n".join(f"{i}: {j}" for i, j in zip(range(max_results), results))
#         time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         prompt = COLLECT_AND_RANKURLS_PROMPT.format(topic=topic, query=query, results=_results, time_stamp=time_stamp)
#         logger.debug(prompt)
#         indices = await self._aask(prompt)
#         try:
#             indices = OutputParser.extract_struct(indices, list)
#             assert all(isinstance(i, int) for i in indices)
#         except Exception as e:
#             logger.exception(f"fail to rank results for {e}")
#             indices = list(range(max_results))
#         results = [results[i] for i in indices]
#         if self.rank_func:
#             results = self.rank_func(results)
#         return [i["link"] for i in results[:num_results]]

#     async def _search_urls(self, query: str, max_results: int) -> list[dict[str, str]]:
#         """Use search_engine to get urls.

#         Returns:
#             e.g. [{"title": "...", "link": "...", "snippet", "..."}]
#         """

#         return await self.search_engine.run(query, max_results=max_results, as_string=False)


# class WebBrowseAndSummarize(Action):
#     """Action class to explore the web and provide summaries of articles and webpages."""

#     name: str = "WebBrowseAndSummarize"
#     i_context: Optional[str] = None
#     desc: str = "Explore the web and provide summaries of articles and webpages."
#     browse_func: Union[Callable[[list[str]], None], None] = None
#     web_browser_engine: Optional[WebBrowserEngine] = None

#     @model_validator(mode="after")
#     def validate_engine_and_run_func(self):
#         if self.web_browser_engine is None:
#             self.web_browser_engine = WebBrowserEngine.from_browser_config(
#                 self.config.browser,
#                 browse_func=self.browse_func,
#                 proxy=self.config.proxy,
#             )
#         return self

#     async def run(
#         self,
#         url: str,
#         *urls: str,
#         query: str,
#         system_text: str = RESEARCH_BASE_SYSTEM,
#         use_concurrent_summarization: bool = False,
#         per_page_timeout: Optional[float] = None,
#     ) -> dict[str, str]:
#         """Run the action to browse the web and provide summaries.

#         Args:
#             url: The main URL to browse.
#             urls: Additional URLs to browse.
#             query: The research question.
#             system_text: The system text.
#             use_concurrent_summarization: Whether to concurrently summarize the content of the webpage by LLM.
#             per_page_timeout: The maximum time for fetching a single page in seconds.

#         Returns:
#             A dictionary containing the URLs as keys and their summaries as values.
#         """
#         contents = await self._fetch_web_contents(url, *urls, per_page_timeout=per_page_timeout)

#         all_urls = [url] + list(urls)
#         summarize_tasks = [self._summarize_content(content, query, system_text) for content in contents]
#         summaries = await self._execute_summarize_tasks(summarize_tasks, use_concurrent_summarization)
#         result = {url: summary for url, summary in zip(all_urls, summaries) if summary}

#         return result

#     async def _fetch_web_contents(
#         self, url: str, *urls: str, per_page_timeout: Optional[float] = None
#     ) -> list[WebPage]:
#         """Fetch web contents from given URLs."""

#         contents = await self.web_browser_engine.run(url, *urls, per_page_timeout=per_page_timeout)

#         return [contents] if not urls else contents

#     async def _summarize_content(self, page: WebPage, query: str, system_text: str) -> str:
#         """Summarize web content."""
#         try:
#             prompt_template = WEB_BROWSE_AND_SUMMARIZE_PROMPT.format(query=query, content="{}")

#             content = page.inner_text

#             if self._is_content_invalid(content):
#                 logger.warning(f"Invalid content detected for URL {page.url}: {content[:10]}...")
#                 return None

#             chunk_summaries = []
#             for prompt in generate_prompt_chunk(content, prompt_template, self.llm.model, system_text, 4096):
#                 logger.debug(prompt)
#                 summary = await self._aask(prompt, [system_text])
#                 if summary == "Not relevant.":
#                     continue
#                 chunk_summaries.append(summary)

#             if not chunk_summaries:
#                 return None

#             if len(chunk_summaries) == 1:
#                 return chunk_summaries[0]

#             content = "\n".join(chunk_summaries)
#             prompt = WEB_BROWSE_AND_SUMMARIZE_PROMPT.format(query=query, content=content)
#             summary = await self._aask(prompt, [system_text])
#             return summary
#         except Exception as e:
#             logger.error(f"Error summarizing content: {e}")
#             return None

#     def _is_content_invalid(self, content: str) -> bool:
#         """Check if the content is invalid based on specific starting phrases."""

#         invalid_starts = ["Fail to load page", "Access Denied"]

#         return any(content.strip().startswith(phrase) for phrase in invalid_starts)

#     async def _execute_summarize_tasks(self, tasks: list[Coroutine[Any, Any, str]], use_concurrent: bool) -> list[str]:
#         """Execute summarize tasks either concurrently or sequentially."""

#         if use_concurrent:
#             return await asyncio.gather(*tasks)

#         return [await task for task in tasks]


# class ConductResearch(Action):
#     """Action class to conduct research and generate a research report."""

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     async def run(
#         self,
#         topic: str,
#         content: str,
#         system_text: str = RESEARCH_BASE_SYSTEM,
#     ) -> str:
#         """Run the action to conduct research and generate a research report.

#         Args:
#             topic: The research topic.
#             content: The content for research.
#             system_text: The system text.

#         Returns:
#             The generated research report.
#         """
#         prompt = CONDUCT_RESEARCH_PROMPT.format(topic=topic, content=content)
#         logger.debug(prompt)
#         self.llm.auto_max_tokens = True
#         return await self._aask(prompt, [system_text])


# def get_research_system_text(topic: str, language: str):
#     """Get the system text for conducting research.

#     Args:
#         topic: The research topic.
#         language: The language for the system text.

#     Returns:
#         The system text for conducting research.
#     """
#     return " ".join((RESEARCH_TOPIC_SYSTEM.format(topic=topic), LANG_PROMPT.format(language=language)))


#!/usr/bin/env python

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional, Union

from pydantic import TypeAdapter, model_validator

from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.tools.search_engine import SearchEngine
from metagpt.tools.web_browser_engine import WebBrowserEngine
from metagpt.utils.common import OutputParser
from metagpt.utils.parse_html import WebPage
from metagpt.utils.text import generate_prompt_chunk, reduce_message_length

LANG_PROMPT = "Please respond in {language}."

# RESEARCH_BASE_SYSTEM = """You are an AI research assistant. Your task is to analyze information critically and produce \
# well-structured, objective reports based on provided sources. Always maintain academic integrity and verify facts."""

RESEARCH_BASE_SYSTEM = """You are an advanced AI research assistant.

Your task is to analyze and synthesize information into a clear, objective, and well-structured research report based on the following user input.
Instructions:
1. Extract the core research topic from the line starting with 'Topic:'.
2. Carefully consider each item under 'User Feedback:' as specific user instructions or modifications (e.g., adding focus areas, improving coverage, or preferred sources).
3. Integrate these feedback points into the report without repeating them explicitly.
4. Uphold academic integrity, evidence-based reasoning, and clarity in your writing.
5. The final output must be in Markdown format and suitable for professional or academic use.
"""


# RESEARCH_TOPIC_SYSTEM = """You are researching: {topic}
# Guidelines:
# 1. Prioritize information from .gov/.edu/.org domains
# 2. Cross-validate facts with multiple sources
# 3. Clearly distinguish between verified facts and interpretations"""

RESEARCH_TOPIC_SYSTEM = """You are tasked with conducting an in-depth, structured investigation on the topic: {topic}.
Guidelines:
1. Prioritize information from .gov/.edu/.org/.com/ domains
2. Cross-validate facts with multiple sources.
3. Clearly distinguish between verified facts and interpretations.
4. You need to also consider the following additional needs of the user (if any): {feedback}"""


SEARCH_TOPIC_PROMPT = """Generate 2-3 optimal search queries for researching: "{topic} and You need to also consider the following additional needs of the user (if any): {feedback}"
Respond in JSON format like: ["query1", "query2"]"""


SUMMARIZE_SEARCH_PROMPT = """Analyze these search results and generate {decomposition_nums} refined queries:
Search Results:
{search_results} Respond with JSON array of queries ordered by priority: ["query1", "query2"]"""

COLLECT_AND_RANKURLS_PROMPT = """You are evaluating {result_count} search results for a query on the following task:

{topic}

Query: "{query}"
Current Time: {time_stamp}

Results:
{results}

Instructions:
1. Remove off-topic or low-quality results
2. Favor .gov/.edu/.org domains
3. Prioritize up-to-date content if applicable

Return ranked indices as JSON array (e.g., [1, 3, 0])"""


WEB_BROWSE_AND_SUMMARIZE_PROMPT = """Analyze this content regarding "{query}":
Source: {url}
Content:
{content}

Summarize key points relevant to the research topic, including:
- Key findings/data
- Methodology (if research)
- Limitations/caveats
- Source credibility indicators

If irrelevant, respond only with "null"."""

CONDUCT_RESEARCH_PROMPT = """Based on the provided web search results, generate a rigorous, well-structured, and in-depth knowledge report on the topic: "{topic} and You need to also consider the following additional needs of the user (if any): {feedback}":
Sources:
{content}

Sources:
{content}

### Report Requirements:
1. 4000+ word academic-quality analysis
2. APA style in-text citations and reference list
3. Comparative tables for quantitative data
4. Critical evaluation of source reliability
5. Professional, academic tone
6. Generate a complete, detailed, and coherent knowledge base that can support future tasks

### Clearly Labeled Sections in Report:
1. Introduction  
   - Define the topic's scope and relevance in 1-2 paragraphs  
   - Briefly explain the purpose of this report and what the reader can expect to learn  

2. Search Results (The core part of the report, Key Findings)  
   - Organize this section into **thematic or topical subheadings** for clarity  
   - Summarize important facts, statistics, insights, and positions found in the sources  
   - Use **APA-style in-text citations with the source URL** (e.g., Author, year, [URL])  
   - Include **comparative tables or lists** where useful to show patterns, differences, or trends  
   - Highlight any **conflicting data or viewpoints**, and identify gaps in the available information 
   - The content of this part should be as complete and detailed as possible. It can be appropriately improved and expanded on the basis of the research results 

3. References  
   - List all sources used, formatted in APA style  
   - Each reference should include:
     - Author or organization
     - Year of publication (or retrieval date if no date available)
     - Title of the article or page
     - URL
"""

class CollectLinks(Action):
    """Enhanced link collection with domain filtering and query optimization"""

    name: str = "CollectLinks"
    desc: str = "Collect and rank relevant URLs from search engines"
    search_engine: Optional[SearchEngine] = None
    min_links_per_query: int = 3
    max_links_per_query: int = 8

    @model_validator(mode="after")
    def validate_engine(self):
        if not self.search_engine:
            self.search_engine = SearchEngine.from_search_config(
                self.config.search, 
                proxy=self.config.proxy
            )
        return self

    async def run(
        self,
        topic: str,
        decomposition_nums: int = 3,
        url_per_query: int = 5,
        system_text: str = None,
        feedback = None
    ) -> dict[str, list[str]]:
        """Collect links with improved query generation and filtering"""
        system_text = system_text or RESEARCH_TOPIC_SYSTEM.format(topic=topic,feedback=feedback)
        # Generate initial queries
        queries = await self._generate_queries(topic, feedback, system_text)
        if not queries:
            queries = [topic]
            
        # Execute searches and refine queries
        refined_queries = await self._refine_queries(
            topic, queries, decomposition_nums, system_text
        )
        
        # Collect and filter URLs
        results = {}
        for query in refined_queries:
            urls = await self._get_ranked_urls(topic, query, url_per_query)
            if urls:
                results[query] = urls
                
        return results

    async def _generate_queries(self, topic: str, feedback: str, system_text: str) -> list[str]:
        """Generate optimized search queries"""
        try:
            response = await self._aask(SEARCH_TOPIC_PROMPT.format(topic=topic,feedback=feedback), [system_text])
            queries = OutputParser.extract_struct(response, list)
            return TypeAdapter(list[str]).validate_python(queries)
        except Exception as e:
            logger.warning(f"Query generation failed: {e}")
            return []

    async def _refine_queries(
        self, 
        topic: str,
        initial_queries: list[str],
        max_queries: int,
        system_text: str
    ) -> list[str]:
        """Refine queries based on initial search results"""
        try:
            search_results = await asyncio.gather(
                *(self.search_engine.run(q, as_string=False) for q in initial_queries
            ))
            
            prompt = SUMMARIZE_SEARCH_PROMPT.format(
                decomposition_nums=max_queries,
                search_results="\n".join(
                    f"Query: {q}\nResults: {r[:2]}" 
                    for q, r in zip(initial_queries, search_results)
            ))
            
            response = await self._aask(prompt, [system_text])
            return OutputParser.extract_struct(response, list)
        except Exception as e:
            logger.warning(f"Query refinement failed: {e}")
            return initial_queries[:max_queries]

    async def _get_ranked_urls(
        self,
        topic: str,
        query: str,
        num_results: int
    ) -> list[str]:
        """Get and rank URLs with domain filtering"""
        try:
            # Get more results than needed for filtering
            results = await self.search_engine.run(
                query, 
                max_results=num_results * 3,
                as_string=False
            )
            
            if not results:
                return []
                
            # Rank results
            ranked_indices = await self._rank_results(topic, query, results)
            ranked_results = [results[i] for i in ranked_indices if i < len(results)]
            
            # Apply domain filtering
            filtered = self._filter_by_domain(ranked_results)
            return [r["link"] for r in filtered[:num_results]]
        except Exception as e:
            logger.error(f"URL collection failed for {query}: {e}")
            return []

    async def _rank_results(
        self,
        topic: str,
        query: str,
        results: list[dict]
    ) -> list[int]:
        """Rank results by relevance and credibility"""
        prompt = COLLECT_AND_RANKURLS_PROMPT.format(
            topic=topic,
            query=query,
            result_count=len(results),
            results="\n".join(f"{i}. {r['title']} ({r['link']})" for i, r in enumerate(results)),
            time_stamp=datetime.now().strftime("%Y-%m-%d")
        )
        
        response = await self._aask(prompt)
        try:
            return OutputParser.extract_struct(response, list)
        except:
            return list(range(len(results)))

    def _filter_by_domain(self, results: list[dict]) -> list[dict]:
        """Filter results by domain authority"""
        preferred_domains = ('.gov', '.edu', '.org')
        return [
            r for r in results
            if any(d in r['link'].lower() for d in preferred_domains)
        ]


class WebBrowseAndSummarize(Action):
    """Enhanced web browsing with content analysis and reliability assessment"""

    name: str = "WebBrowseAndSummarize"
    desc: str = "Browse web pages and extract structured summaries"
    web_browser_engine: Optional[WebBrowserEngine] = None
    max_retries: int = 2
    timeout: float = 15.0

    @model_validator(mode="after")
    def validate_engine(self):
        if not self.web_browser_engine:
            self.web_browser_engine = WebBrowserEngine.from_browser_config(
                self.config.browser,
                proxy=self.config.proxy
            )
        return self

    async def run(
        self,
        url: str,
        *urls: str,
        query: str,
        system_text: str = RESEARCH_BASE_SYSTEM,
        **kwargs
    ) -> dict[str, str]:
        """Browse URLs and return analyzed summaries"""
        all_urls = [url] + list(urls)
        contents = await self._fetch_with_retry(all_urls)
        
        summaries = {}
        for url, content in zip(all_urls, contents):
            if content:
                summary = await self._analyze_content(content, query, system_text)
                if summary and summary.lower() != "null":
                    summaries[url] = summary
                    
        return summaries

    async def _fetch_with_retry(self, urls: list[str]) -> list[WebPage]:
        """Fetch web content with retry mechanism"""
        tasks = [self._fetch_single(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def _fetch_single(self, url: str) -> Optional[WebPage]:
        """Fetch single URL with retry"""
        for attempt in range(self.max_retries + 1):
            try:
                result = await self.web_browser_engine.run(
                    url
                )
                if isinstance(result, list):
                    return result[0] if result else None
                return result
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Failed to fetch {url}: {e}")
                    return None
                await asyncio.sleep(1 * (attempt + 1))

    async def _analyze_content(
        self,
        page: WebPage,
        query: str,
        system_text: str
    ) -> Optional[str]:
        """Analyze and summarize web content"""
        try:
            if not page.inner_text or self._is_invalid(page):
                return None
                
            prompt = WEB_BROWSE_AND_SUMMARIZE_PROMPT.format(
                query=query,
                url=page.url,
                content=page.inner_text[:20000]  # Limit content size
            )
            
            return await self._aask(prompt, [system_text])
        except Exception as e:
            logger.error(f"Content analysis failed for {page.url}: {e}")
            return None

    def _is_invalid(self, page: WebPage) -> bool:
        """Check for invalid/blocked content"""
        invalid_indicators = [
            "access denied",
            "404 not found",
            "this page cannot be displayed"
        ]
        text = page.inner_text.lower()
        return any(indicator in text for indicator in invalid_indicators)


class ConductResearch(Action):
    """Enhanced research synthesis with RAG integration"""

    name: str = "ConductResearch"
    desc: str = "Synthesize research findings into comprehensive report"
    min_report_length: int = 5000
    citation_style: str = "APA"

    async def run(
        self,
        topic: str,
        content: str,
        feedback: str,
        system_text: str = RESEARCH_BASE_SYSTEM,
        **kwargs
    ) -> str:
        """Generate research report with source verification"""
        try:
            # Pre-process content for RAG
            structured_content = self._structure_content(content)
            
            prompt = CONDUCT_RESEARCH_PROMPT.format(
                topic=topic,
                feedback = feedback,
                content=structured_content
            )
            
            report = await self._generate_report(prompt, system_text)
            return self._post_process(report, content)
        except Exception as e:
            logger.error(f"Research synthesis failed: {e}")
            return f"Research failed: {str(e)}"

    def _structure_content(self, raw_content: str) -> str:
        """Structure content for better RAG processing"""
        sections = []
        for part in raw_content.split("\n---\n"):
            if "url:" in part and "summary:" in part:
                url = part.split("url:")[1].split("\n")[0].strip()
                summary = part.split("summary:")[1].strip()
                sections.append(f"## Source: {url}\n{summary}")
        return "\n\n".join(sections)

    async def _generate_report(self, prompt: str, system_text: str) -> str:
        """Generate report with length validation"""
        self.llm.auto_max_tokens = True
        report = await self._aask(prompt, [system_text])
        
        # Ensure minimum length
        if len(report.split()) < self.min_report_length * 0.8:  # 80% threshold
            logger.warning("Report too short, regenerating...")
            report += "\n\n" + await self._aask(
                "Continue to expand the content of this report and be as detailed as possible, expand the report to meet length requirements",
                [system_text]
            )
        return report

    def _post_process(self, report: str, sources: str) -> str:
        """Add citations and formatting"""
        # Extract URLs from sources
        urls = []
        for line in sources.split("\n"):
            if line.startswith("url:"):
                urls.append(line[4:].strip())
                
        # Add references section
        if urls:
            ref_section = "\n\n## References\n" + "\n".join(
                f"- {self._format_citation(url)}" 
                for url in set(urls)  # Remove duplicates
            )
            report += ref_section
            
        return report

    def _format_citation(self, url: str) -> str:
        """Format citation in specified style"""
        if self.citation_style == "APA":
            return f"Retrieved from {url}"
        return url


def get_research_system_text(topic: str, language: str, feedback: str) -> str:
    """Generate system prompt for research tasks"""
    base = RESEARCH_TOPIC_SYSTEM.format(topic=topic,feedback=feedback)
    lang = LANG_PROMPT.format(language=language)
    return f"{base}\n{lang}"