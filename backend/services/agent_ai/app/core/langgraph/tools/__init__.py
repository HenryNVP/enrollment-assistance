"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Currently includes tools for web search,
RAG document search, course prerequisites, and program structure.
"""

from langchain_core.tools.base import BaseTool

from .duckduckgo_search import duckduckgo_search_tool
from .rag_search import rag_search_tool
from .course_prereqs import course_prereqs_tool
from .program_requirements import program_requirements_tool

tools: list[BaseTool] = [
    duckduckgo_search_tool,
    rag_search_tool,
    course_prereqs_tool,
    program_requirements_tool,
]
