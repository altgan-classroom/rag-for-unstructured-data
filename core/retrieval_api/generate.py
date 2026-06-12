import logging
import json
import tiktoken  # For token counting
import uuid
import time
import warnings
import re
from pathlib import Path
from typing import Optional, Dict, Generator, List, Any, Union, Tuple, Callable, AsyncGenerator
from pydantic import BaseModel
from urllib.parse import quote
from datetime import datetime

import qdrant_client
import asyncio
import nest_asyncio
from tavily import TavilyClient
from llama_index.core import StorageContext, Settings, load_index_from_storage,PromptHelper,VectorStoreIndex
from llama_index.core.schema import QueryBundle, Node
from llama_index.core.query_engine import CitationQueryEngine

from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine
# from llama_index.experimental.question_gen.llm_generators import SubQuestionGenerator

# from llama_index.core.question_gen.llm_generators import SubQuestionGenerator
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler

from llama_index.core import Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.schema import TextNode,NodeWithScore
from llama_index.core.postprocessor import LLMRerank

from .managers.storage_manager import StorageManager
from .managers.llm_manager import LLMManager
from .managers.prompt_manager import PromptManager
from .retrievers.compound_retriever import CompoundQueryRetriever

warnings.filterwarnings("ignore")

# Configure environment
nest_asyncio.apply()

logger = logging.getLogger(__name__)


class Generate:
    """Class for generating responses using RAG.
    This class is doing
        1. getting configd and secrets
        2. getting request related data
        3. getting storage manager, LLM manager 
        4. Preparing the query
        7. getting response from query engine
        8. gets responses for is_greeting, is_compoundquery and handle_compund_queries
    """

    def __init__(
        self,
        config: Callable[[str], Any],
        secret: Callable[[str], Any],
        chat_id: str,
        query: str,
        category_name: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        persist_dir: str = "persist",
        collection_name: str = "rag_llm",
        s3_manager: Optional[Any] = None,
        storage_manager: StorageManager = None,
        llm_manager: LLMManager = None,
        index: VectorStoreIndex = None,
        query_engine: CitationQueryEngine = None,
        is_web_search: bool = True,
    ):
        """Initialize the Generate class."""
        self._config = config
        self._secret = secret
        self._chat_id = chat_id
        self._query = query
        self._category_name = category_name
        self._metadata = metadata or {}
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._s3_manager = s3_manager
        self._llm_manager = llm_manager
        self._is_web_search = is_web_search

        
        # Get API keys from config instead of secrets
        self._tavily_api_key = self._secret("TAVILY_API_KEY")
        self._openai_api_key = self._secret("OPENAI_API_KEY")
        self._anthropic_api_key = self._secret("ANTHROPIC_API_KEY")
        self._cohere_api_key = self._secret("COHERE_API_KEY")

        logger.info(f"Initializing Generate for category: {category_name}")
        self._prompts = PromptManager.load_prompts(self._config)
        self._model_manager = self._llm_manager

        # Load chat history and prepare query
        self._storage_manager = storage_manager
        self.query_engine = query_engine
        # self._index = index


        # self._storage_manager.load_chat_history(chat_id)
        try:
            enc = tiktoken.encoding_for_model(self._model_manager.model_name)  # Or your model's encoding

            chat_hist_tokens = len(enc.encode(str(self._storage_manager._chat_hist)))
            logger.debug(f"chat_hist_tokens, {chat_hist_tokens}")
        except Exception as e:
            logger.info(f"error in printing tokens: {e}")

        # self._refined_query = self._prepare_query()
        self._refined_query = self._query


    def _prepare_query(self) -> str:
        """Prepare the refined query with chat history."""
        if self._storage_manager.chat_hist is not None:
            return f"<|CHAT HISTORY|>: {self._storage_manager.chat_hist}\n\n<|QUERY|>: {self._query}"
        return f"<|QUERY|>: {self._query}"

    async def _is_greeting(self):
        response_ = await self._model_manager.llm.acomplete(
                self._prompts.greeting_classifier.format(query=self._query)
            )
        is_greeting = response_.text.strip()
        logger.info(f"is_greeting, {is_greeting}")
        return is_greeting

    async def _handle_greeting(self):
        logger.info("Query classified as greeting")
        greeting_prompt = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self._prompts.system_prompt,
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=self._prompts.greeting.format(query=self._query),
            ),
        ]
        # greeting_response = self._model_manager.llm.stream_chat(greeting_prompt)
        for text in self._model_manager.llm.stream_chat(greeting_prompt):
            # logger.info(f"Yielding message {text.delta}")  # Debugging log
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "greeting",
                "text": text.delta,
            })

    async def generate_answer(self) -> AsyncGenerator[str, None]:
        """Async generator that yields chat responses for the given query."""
        try:
            logger.debug("Checking if query is a greeting")

            if self._model_manager.llm is None:
                logger.error("LLM model is None! Check initialization.")
                raise ValueError("LLM model is not initialized.")
            start_time = time.perf_counter()

            is_greeting = await self._is_greeting()
            logger.info(f"greeting classified at: {time.perf_counter() - start_time}")
            if is_greeting is True:
                logger.info("[Greeting Handler] Entering greeting handler.")
                async for chunk in self._handle_greeting():
                    yield chunk
                return
                
            # Retrieve documents
            retrieved_docs = await self._retrieve_documents()
            logger.info(f"Time taken for document retrieval: {time.perf_counter() - start_time}, number of docs : {len(retrieved_docs)}")


            if not self._has_valid_docs(retrieved_docs):
                if self._is_web_search:
                    async for chunk in self._websearch():
                        yield chunk
                else:
                    for chunk in self._handle_no_retrieval_results():
                        yield chunk
                return

            # Generate response
            logger.info("Generating response...")
            logger.info(f"refined_query {self._refined_query}")
            response = await self.query_engine.asynthesize(
                query_bundle=QueryBundle(query_str=self._refined_query),
                nodes=retrieved_docs,
            )
            

            answer = ""
            first_token_time = None
            if response:
                logger.info(f"asynthesize done at : {time.perf_counter() - start_time}")
                async for text in response.response_gen:
                    if text != "Empty Response":
                        answer += text
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                            logger.info(f"first token generated at : {first_token_time - start_time}")
                    yield json.dumps({
                        "response_id": str(uuid.uuid4()),
                        "type": "tokens",
                        "text": text,
                    })
            else:
                async for chunk in self._handle_no_retrieval_results():
                    yield chunk
                return
            logger.info(f"Answer generated at : {time.perf_counter() - start_time}")
           

            # Process contexts and citations
            contexts, answer = await self._process_contexts(answer, response.source_nodes, retrieved_docs)
            async for chunk in self._yield_context_answer(contexts, answer):
                yield chunk
            
            logger.info(f"processed contexts and citations at : {time.perf_counter() - start_time}")

            # Get Related Queries
            if answer:
                async for chunk in self._get_related_queries(response, answer):
                    yield chunk

            logger.info(f"related queries at : {time.perf_counter() - start_time}")
            # Token counting (optional, keep sync if no I/O involved)
            try:
                enc = tiktoken.encoding_for_model(self._model_manager.model_name)
                answer_tokens = len(enc.encode(str(answer)))
                query_tokens = len(enc.encode(str(self._query)))
                logger.debug(f"Query tokens: {query_tokens}, Answer tokens: {answer_tokens}")
            except Exception as e:
                logger.error(f"Error counting tokens: {e}")

            # Generate conversation title if no chat history
            try:
                if self._storage_manager.chat_hist is None:
                    async for chunk in self._generate_conversation_title():
                        yield chunk
                    logger.info(f"conversation title generated at : {time.perf_counter() - start_time}")
            except Exception as e:
                logger.critical(f"Error generating conversation title: {e}")
            
            # Update chat history
            self._storage_manager.chat_hist = f"{self._refined_query}\n{answer}\n\n"
            logger.info("Successfully completed response generation")

        except asyncio.CancelledError:
            logger.warning("Client disconnected, stopping response generation.")
            return

        except Exception as e:
            logger.critical(f"Error generating answer: {e}")
            raise

    async def generate_report(self) -> Generator[str, None, None]:
        """Async generator that yields chat responses for the given query."""
        try:
            logger.debug("Checking if query is a greeting")

            if self._model_manager.llm is None:
                logger.error("LLM model is None! Check initialization.")
                raise ValueError("LLM model is not initialized.")
            start_time = time.perf_counter()

            is_greeting = await self._is_greeting()
            logger.info(f"greeting classified at: {time.perf_counter() - start_time}")
            if is_greeting is True:
                logger.info("[Greeting Handler] Entering greeting handler.")
                async for chunk in self._handle_greeting():
                    yield chunk
                return
                
            # Retrieve documents
            retrieved_docs = await self._retrieve_documents_report()
            logger.info(f"Time taken for document retrieval: {time.perf_counter() - start_time}, number of docs : {len(retrieved_docs)}")


            if not self._has_valid_docs_report(retrieved_docs):
                if self._is_web_search:
                    async for chunk in self._websearch():
                        yield chunk
                else:
                    for chunk in self._handle_no_retrieval_results():
                        yield chunk
                return

            # Generate response
            logger.info("Generating response...")
            # TODO CODE TO PRINT TOKENS HERE
            # Change synthesizing prompt to report synthesizing prompt

            logger.info(f"refined_query {self._refined_query}")
            response = await self.query_engine.asynthesize(
                query_bundle=QueryBundle(query_str=self._refined_query),
                nodes=retrieved_docs,
            )
            

            answer = ""
            first_token_time = None
            if response:
                logger.info(f"asynthesize done at : {time.perf_counter() - start_time}")
                async for text in response.response_gen:
                    if text != "Empty Response":
                        answer += text
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                            logger.info(f"first token generated at : {first_token_time - start_time}")
                    yield json.dumps({
                        "response_id": str(uuid.uuid4()),
                        "type": "tokens",
                        "text": text,
                    })
            else:
                async for chunk in self._handle_no_retrieval_results():
                    yield chunk
                return
            logger.info(f"Answer generated at : {time.perf_counter() - start_time}")
           

            # Process contexts and citations
            contexts, answer = await self._process_contexts(answer, response.source_nodes, retrieved_docs)
            async for chunk in self._yield_context_answer(contexts, answer):
                yield chunk
            
            logger.info(f"processed contexts and citations at : {time.perf_counter() - start_time}")

            # Get Related Queries
            if answer:
                async for chunk in self._get_related_queries(response, answer):
                    yield chunk

            logger.info(f"related queries at : {time.perf_counter() - start_time}")
            # Token counting (optional, keep sync if no I/O involved)
            try:
                enc = tiktoken.encoding_for_model(self._model_manager.model_name)
                answer_tokens = len(enc.encode(str(answer)))
                query_tokens = len(enc.encode(str(self._query)))
                logger.debug(f"Query tokens: {query_tokens}, Answer tokens: {answer_tokens}")
            except Exception as e:
                logger.error(f"Error counting tokens: {e}")

            # Generate conversation title if no chat history
            try:
                if self._storage_manager.chat_hist is None:
                    async for chunk in self._generate_conversation_title():
                        yield chunk
                    logger.info(f"conversation title generated at : {time.perf_counter() - start_time}")
            except Exception as e:
                logger.critical(f"Error generating conversation title: {e}")
            
            # Update chat history
            self._storage_manager.chat_hist = f"{self._refined_query}\n{answer}\n\n"
            logger.info("Successfully completed response generation")

        except asyncio.CancelledError:
            logger.warning("Client disconnected, stopping response generation.")
            return

        except Exception as e:
            logger.critical(f"Error generating answer: {e}")
            raise

    async def generate_report_subanswer_append(self) -> Generator[str, None, None]:
        """Async generator that yields chat responses for the given query."""
        try:
            logger.debug("Checking if query is a greeting")

            if self._model_manager.llm is None:
                logger.error("LLM model is None! Check initialization.")
                raise ValueError("LLM model is not initialized.")
            start_time = time.perf_counter()

            is_greeting = await self._is_greeting()
            logger.info(f"greeting classified at: {time.perf_counter() - start_time}")
            if is_greeting is True:
                logger.info("[Greeting Handler] Entering greeting handler.")
                async for chunk in self._handle_greeting():
                    yield chunk
                return
                
            # Retrieve documents
            # retrieved_docs = await self._retrieve_documents_report()
            report_query_bundle = await self.query_engine.get_report_subqueries(QueryBundle(query_str=self._refined_query))
            logger.info(f"Time taken for document retrieval: {time.perf_counter() - start_time}, number of queries : {len(report_query_bundle)}")

            # if not self._has_valid_docs_report(retrieved_docs):
            #     if self._is_web_search:
            #         async for chunk in self._websearch():
            #             yield chunk
            #     else:
            #         for chunk in self._handle_no_retrieval_results():
            #             yield chunk
            #     return

            # Generate response
            logger.info("Generating response...")
            # TODO CODE TO PRINT TOKENS HERE
            # Change synthesizing prompt to report synthesizing prompt

            logger.info(f"refined_query {self._refined_query}")

            sub_query_outputs = await self.run_all_subqueries(report_query_bundle)
            async for chunk in self.stream_report_as_json(sub_query_outputs):
                yield chunk

            # realigned_text, citation_text_map = self.realign_citations(sub_query_outputs)
            # response = await self.generate_final_summary(query_bundle=QueryBundle(query_str=self._refined_query), full_context=realigned_text)
            # response = await self.query_engine.asynthesize(
            #     query_bundle=QueryBundle(query_str=self._refined_query),
            #     nodes=retrieved_docs,
            # )

            # async for chunk in self.stream_summary_response(QueryBundle(query_str=self._refined_query), realigned_text):
            #     yield chunk
            # answer = ""
            # first_token_time = None
            # # if response:
            # #     logger.info(f"asynthesize done at : {time.perf_counter() - start_time}")
            # #     async for text in response.response_gen:
            # #         if text != "Empty Response":
            # #             answer += text
            # #             if first_token_time is None:
            # #                 first_token_time = time.perf_counter()
            # #                 logger.info(f"first token generated at : {first_token_time - start_time}")
            # #         yield json.dumps({
            # #             "response_id": str(uuid.uuid4()),
            # #             "type": "tokens",
            # #             "text": text,
            # #         })
            # # else:
            # #     async for chunk in self._handle_no_retrieval_results():
            # #         yield chunk
            # #     return
            logger.info(f"Answer generated at : {time.perf_counter() - start_time}")
            # logger.info(f"Answer: {answer}")
           

            # # Process contexts and citations
            # contexts, answer = await self._process_contexts(answer, response.source_nodes, retrieved_docs)
            # async for chunk in self._yield_context_answer(contexts, answer):
            #     yield chunk
            
            # logger.info(f"processed contexts and citations at : {time.perf_counter() - start_time}")

            # # Get Related Queries
            # if answer:
            #     async for chunk in self._get_related_queries(response, answer):
            #         yield chunk

            # logger.info(f"related queries at : {time.perf_counter() - start_time}")
            # # Token counting (optional, keep sync if no I/O involved)
            # try:
            #     enc = tiktoken.encoding_for_model(self._model_manager.model_name)
            #     answer_tokens = len(enc.encode(str(answer)))
            #     query_tokens = len(enc.encode(str(self._query)))
            #     logger.debug(f"Query tokens: {query_tokens}, Answer tokens: {answer_tokens}")
            # except Exception as e:
            #     logger.error(f"Error counting tokens: {e}")

            # # Generate conversation title if no chat history
            # try:
            #     if self._storage_manager.chat_hist is None:
            #         async for chunk in self._generate_conversation_title():
            #             yield chunk
            #         logger.info(f"conversation title generated at : {time.perf_counter() - start_time}")
            # except Exception as e:
            #     logger.critical(f"Error generating conversation title: {e}")
            
            # Update chat history
            # self._storage_manager.chat_hist = f"{self._refined_query}\n{answer}\n\n"
            # logger.info("Successfully completed response generation")

        except asyncio.CancelledError:
            logger.warning("Client disconnected, stopping response generation.")
            return

        except Exception as e:
            logger.critical(f"Error generating answer: {e}")
            raise

    def _handle_no_retrieval_results(self):
        logger.info("landed into no retieval results")
        # Yield a message suggesting the user to refine their query
        yield json.dumps({
            "response_id": str(uuid.uuid4()),
            "type": "answer",
            "text": (
                "I couldn’t find any relevant information based on your query in the current knowledge base. "
                "Please try rephrasing your question or include more specific details to help improve the results."
            )
        })
        # Yield a context type response with an empty context and prompt user for more details
        yield json.dumps({
            "response_id": str(uuid.uuid4()),
            "type": "context",
            "text": json.dumps({})  # No context found
        })

    async def _retrieve_documents(self):
        logger.info("Retrieving relevant documents...")
        retrieved_docs = await self.query_engine.aretrieve(QueryBundle(query_str=self._refined_query))
        logger.info(f"Score of retrieved docs: {[doc.score for doc in retrieved_docs]}")
        return retrieved_docs
    
    async def _retrieve_documents_report(self):
        logger.info("Retrieving relevant documents...")
        retrieved_docs = await self.query_engine._aretrieve_report(QueryBundle(query_str=self._refined_query))
        logger.info(f"Score of retrieved docs: {[doc.score for doc in retrieved_docs]}")
        return retrieved_docs
    
    async def run_all_subqueries(self, sub_queries: List[QueryBundle]) -> List[Dict[str, Any]]:
        tasks = [self._summarize_subquery(sub_query, idx) for idx, sub_query in enumerate(sub_queries)]
        return await asyncio.gather(*tasks)

    async def _summarize_subquery(self, sub_query: QueryBundle, idx: int) -> Dict[str, Any]:
        """Summarize a single subquery and return its answer."""
        logger.info(f"Summarizing subquery {idx + 1}: {sub_query.query_str}")
        retrieved_nodes = await self.query_engine.aretrieve(sub_query)
        response = await self.query_engine.asynthesize(query_bundle=sub_query, nodes=retrieved_nodes)
        citations = response.source_nodes if hasattr(response, "source_nodes") else []
        logger.info(f"num docs: {len(retrieved_nodes)}, answer: {response}")
        return {
            "sub_query": sub_query,
            "index": idx,
            "summary": response.response if hasattr(response, "response") else response,
            "citations": citations,
        }

    async def stream_report_from_subqueries(self, subquery_outputs: List[Dict[str, Any]]):
        yield "## Technical Report\n\n"

        for output in subquery_outputs:
            sub_query = output["sub_query"].query_str
            logger.info(f" retrieved answer {output['summary']}")
            answer = output["summary"]
            idx = output["index"] + 1

            section = f"""{answer}\n\n"""
            yield section
    
    async def stream_report_as_json(self, subquery_outputs):
        async for section in self.stream_report_from_subqueries(subquery_outputs):
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "tokens",
                "text": section,
            })

    def realign_citations(self, sub_query_outputs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Realign citations from subquery answers to the main query."""
        try:
            citation_map = {}
            citation_text_map = {}
            citation_index = 1
            all_text = []
            for output in sub_query_outputs:
                sub_query = output["sub_query"]
                index = output["index"]
                text = output["summary"]
                citations = output["citations"]
                # logger.info(f"citations: {citations}")
                for node in citations:
                    node_hash = hash(node.node.get_content())
                    logger.info(f"node_hash: {node_hash}, node.metadata: {node.metadata}")
                    original_citation = str(node.metadata.get("citation", ""))
                    if node_hash not in citation_map:
                        # Create a unique identifier for the node
                        citation_map[node_hash] = {
                            "doc_name": node.metadata["doc_name"],
                            "page_num": node.metadata["page_number"],
                            "text": node.text.strip(),
                            "s3_url": node.metadata.get("s3_url")
                        }
                        node_id = f"doc_{citation_index}"
                        citation_map[node_hash] = citation_index
                        citation_text_map[citation_index] = original_citation
                        citation_index += 1
                    import re
                    pattern = re.escape(original_citation)
                    # Replace the original citation with the new node ID in the text
                    logger.info(f"Replacing '{original_citation}' with '[{citation_map[node_hash]}]' in {text}.")
                    text = re.sub(rf'\b{pattern}\b', f"[{citation_map[node_hash]}]", text)
                all_text.append(text)
            full_text = "\n".join(all_text)
        except Exception as e:
            logger.error(f"Error in realigning citations: {e}")
            full_text = "Error generating summary. Please try again later."
            citation_text_map = {}

        return full_text, citation_text_map
    
    # async def generate_final_summary(self, query_bundle: QueryBundle, full_context: str) -> str:
    #     # citation_list_text = "\n".join([f"[{idx}]: {text}" for idx, text in citation_text_map.items()])
    #     final_prompt = self._prompts.report_append_summarizer.format(query_str=query_bundle.query_str,
    #         full_context=full_context,
    #         # citation_list_text=citation_list_text
    #     )
    #     response = await self.query_engine.aquery(final_prompt)
    #     logger.info(f"response: {response}")
    #     return response.response if hasattr(response, "response") else response

    async def generate_final_summary_stream(self, query_bundle: QueryBundle, full_context: str):
        try:
            logger.info(f"Generating final summary stream...{full_context}")
            # citation_list_text = "\n".join([f"[{idx}]: {text
            final_prompt = self._prompts.report_append_summarizer.format(
                query_str=query_bundle.query_str,
                full_context=full_context,
            )

            llm = self._model_manager.llm  # Use the underlying LLM directly
            from llama_index.core.llms import ChatMessage

            messages = [ChatMessage(role="user", content=final_prompt)]
            response = llm.complete(final_prompt)
            # If response has `.text` or `.response` property, get the text
            text = getattr(response, "text", None) or getattr(response, "response", None) or str(response)
            yield text  # Yield the entire completion as a single chunk
        except Exception as e:
            logger.error(f"Error in generate_final_summary_stream: {e}")
            yield "Error generating summary. Please try again later."
 
    async def stream_summary_response(self, query_bundle: QueryBundle, realigned_text: str):
        start_time = time.perf_counter()
        first_token_time = None
        answer = ""

        try:
            summary_generator = self.generate_final_summary_stream(query_bundle, realigned_text)
            async for text in summary_generator:
                if text.strip():
                    answer += text
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                        logger.info(f"first token generated at : {first_token_time - start_time}")

                    yield json.dumps({
                        "response_id": str(uuid.uuid4()),
                        "type": "tokens",
                        "text": text,
                    })

            if not answer.strip():
                raise ValueError("Empty stream")

        except Exception as e:
            logger.warning(f"Streaming summary failed: {e}")
            for chunk in self._handle_no_retrieval_results():
                yield chunk

    def _has_valid_docs(self, docs):
        if docs and max([doc.score for doc in docs]) > self._config("RAG_SIMILARITY_CUTOFF"):
            return True
        else:
            return False
    
    def _has_valid_docs_report(self, docs):
        if len(docs) > 0 :
            return True
        else:
            return False

    def _decompose_query(self, query: str) -> List[str]:
        try:
            chat_sub_query_prompt = self._prompts.chat_subquery.format(query =query)
            response = self._model_manager.llm.complete(chat_sub_query_prompt).text.strip()
            subqueries = self._parse_subqueries(response)
            if isinstance(subqueries, list) and all(isinstance(q, str) for q in subqueries):
                return subqueries
            else:
                raise ValueError("Invalid format: not a list of strings")
        except json.JSONDecodeError as e:
            raise ValueError(f"Subquery response not valid JSON: {e}")

    def get_subqueries(self, main_query: str, first_pass_answer:str):
        try:
            logger.info("getting sub queries")
            response = self._model_manager.llm.complete(
                    self._prompts.subquery.format(query=main_query,first_pass_answer=first_pass_answer)
                ).text.strip()
            subqueries = self._parse_subqueries(response)
            logger.info("subqueries, {subqueries}")
            if isinstance(subqueries, list) and all(isinstance(q, str) for q in subqueries):
                    return subqueries
            else:
                raise ValueError("Invalid format: not a list of strings")
        except json.JSONDecodeError as e:
            raise ValueError(f"Subquery response not valid JSON: {e}")

    def _handle_compound_query_response(self):
        query_b = QueryBundle(query_str=self._refined_query)
        sub_queries = self._decompose_query(query_b)
        if sub_queries:
            logger.info(f"sub_queries, {sub_queries}")
            subq_answers, retrieved_docs,subq_source_nodes = self._handle_sub_queries(sub_queries)
            # logger.info(f"final_answer, {subq_answers}")
            # response = self._chat_synthesize_response(query_b, subq_answer)
            response = self._chat_synthesize_subanswers(query_b, subq_answers)
            return response
        return
    
    def _yield_compound_response(self, response):
        answer = ""
        if response:
            for chunk_json in self.response_generator(response.text):
                    chunk = json.loads(chunk_json)["text"]
                    if chunk != "Empty Response":
                        answer += chunk
                    yield chunk_json
        else:
            logger.warning("No sub queries/response found")
            if self._is_web_search != "True":
                yield json.dumps({
                    "response_id": str(uuid.uuid4()),
                    "type": "answer",
                    "text": "No relevant contexts retrieved",
                })
                return
            
    def _yield_response_gen(self, response):
        answer = ""
        for text in response.response_gen:
            if text != "Empty Response":
                answer += text
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "tokens",
                "text": text,
                })

    async def _get_answer_from_response(self, response):
        answer = ""
        async for text in response.response_gen:
            if text != "Empty Response":
                answer += text
        logger.debug(f"answer, {answer}")
        return answer
    
    def _get_answer_from_compound_response(self, response):
        answer = ""
        for chunk_json in self.response_generator(response.text):
            chunk = json.loads(chunk_json)["text"]
            if chunk != "Empty Response":
                answer += chunk
        return answer

    
    def _yield_response(self, response):
        answer = ""
        for chunk_json in self.response_generator(response.text):
            chunk = json.loads(chunk_json)["text"]
            if chunk != "Empty Response":
                answer += chunk
            yield chunk_json
    
    def _handle_compound_query_v2(self):
        query_b = QueryBundle(query_str=self._refined_query)
        sub_queries = self._decompose_query(query_b)
        if sub_queries:
            logger.info(f"sub_queries, {sub_queries}")
            subq_answers, retrieved_docs, subq_source_nodes = self._handle_sub_queries_v2(sub_queries)
            global_citation_map = self._build_citationmap(retrieved_docs)
            updated_subq_answers=self._process_sub_queries(sub_queries,subq_answers,subq_source_nodes,global_citation_map)
            sources_text = self._inputs_for_process_cntxt(global_citation_map)
            ordered_docs, ordered_nodes = self._ordered_docs(global_citation_map,retrieved_docs,subq_source_nodes)
            return updated_subq_answers, sources_text,ordered_docs, ordered_nodes
            # # logger.info(f"final_answer, {subq_answers}")
            # # response = self._chat_synthesize_response(query_b, subq_answer)
            # response = self._chat_synthesize_subanswers_v2(self._refined_query, updated_subq_answers, sources_text)
            # # response = self._chat_synthesize_subanswers(query_b, subq_answers)
            # return response

    def _handle_compound_query(self):
        query_b = QueryBundle(query_str=self._refined_query)
        sub_queries = self._decompose_query(query_b)
        if sub_queries:
            logger.debug(f"sub_queries, {sub_queries}")
            subq_answers, retrieved_docs, subq_source_nodes = self._handle_sub_queries_v2(sub_queries)
            global_citation_map = self._build_citationmap(retrieved_docs)
            updated_subq_answers=self._process_sub_queries(sub_queries,subq_answers,subq_source_nodes,global_citation_map)
            sources_text = self._inputs_for_process_cntxt(global_citation_map)
            # logger.info(f"final_answer, {subq_answers}")
            # response = self._chat_synthesize_response(query_b, subq_answer)
            response = self._chat_synthesize_subanswers_v2(self._refined_query, updated_subq_answers, sources_text)
            # response = self._chat_synthesize_subanswers(query_b, subq_answers)
            answer = ""

            for chunk_json in self.response_generator(response.text):
                chunk = json.loads(chunk_json)["text"]
                if chunk != "Empty Response":
                    answer += chunk
                yield chunk_json
        else:
            logger.warning("No sub queries found")
            if self._is_web_search != "True":
                yield json.dumps({
                    "response_id": str(uuid.uuid4()),
                    "type": "answer",
                    "text": "No relevant contexts retrieved",
                })
                return
    
    async def _websearch(self):
        logger.warning("No relevant contexts retrieved")
        if self._is_web_search != "True":
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "answer",
                "text": "No relevant contexts retrieved",
            })
            return

        search_results = self._tavily_client.search(
            self._query, max_results=3, search_depth="advanced"
        )["results"]
        content = "\n\n".join([
            f"{idx+1}. Title: {result['title']}\nContent: {result['content']}\nURL: {result['url']}"
            for idx, result in enumerate(search_results)
        ])
        tavily_prompt = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self._prompts.system_prompt,
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=self._prompts.tavily_template.format(
                    search_results=content, query=self._query
                ),
            ),
        ]

        tavily_resp = self._model_manager.llm_model.stream_chat(tavily_prompt)

        for text in tavily_resp:
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "tokens",
                "text": text.delta,
            })

    def _handle_sub_queries(self, sub_queries: List[str]):
        """
        Process sub-queries, retrieve docs, and return final response.
        """
        retrieved_docs = []
        sub_answers = []
        subq_source_nodes = []
        for sub_query in sub_queries:
            if sub_query:
                logger.info(f"Processing sub-query: {sub_query.strip()}")
                docs = self.query_engine.retrieve(QueryBundle(sub_query.strip()))
                answer = self.query_engine.query(sub_query.strip())
                sub_answers.append(f"**Q:** {sub_query.strip()}\n**A:** {str(answer)}")
                retrieved_docs.extend(docs)
                subq_source_nodes.append(answer.source_nodes)
            
        # Combine sub-answers into a final response
        final_response = "\n\n".join(sub_answers)
        return final_response,retrieved_docs,subq_source_nodes
    
    def _handle_sub_queries_v2(self, sub_queries: List[str]):
        """
        Process sub-queries, retrieve docs, and return final response.
        """
        retrieved_docs = {}
        subq_answers = {}
        subq_source_nodes = {}
        for sub_query in sub_queries:
            if sub_query:
                logger.info(f"Processing sub-query: {sub_query.strip()}")
                docs = self.query_engine.retrieve(QueryBundle(sub_query.strip()))
                answer = self.query_engine.query(sub_query.strip())
                subq_answers[sub_query] = answer
                # logger.info(subq_answers)
                retrieved_docs[sub_query] = docs
                subq_source_nodes[sub_query] = answer.source_nodes
            
        # Combine sub-answers into a final response
        # final_response = "\n\n".join(subq_answers)
        return subq_answers,retrieved_docs,subq_source_nodes
    
    def _build_citationmap(self,retrieved_docs):
        logger.info("building global citation map")
        # Flatten all retrieved_docs across subqueries
        all_docs = []
        seen_texts = set()
        citation_map = {}
        citation_id = 1
        for docs in retrieved_docs.values():
            for doc in docs:
                if doc.text.strip() not in seen_texts:
                    seen_texts.add(doc.text.strip())
                    citation_map[str(citation_id)] = {
                        "doc_name": doc.metadata["doc_name"],
                        "page_num": doc.metadata["page_number"],
                        "text": doc.text.strip(),
                        "s3_url": doc.metadata.get("s3_url")
                    }
                    citation_id += 1
        return citation_map
        # text_to_global_id = {
        #     v["text"]: k for k, v in citation_map.items()
        # }
    import re

    def remap_citations(self, subquery_answer: str, source_nodes: List[Node], global_citation_map: Dict[str, Any]) -> str:
        logger.info("remapping citations")
        updated_answer = subquery_answer
        for i, node in enumerate(source_nodes):
            node_text = node.node.get_text().strip()
            for global_id, meta in global_citation_map.items():
                if node_text == meta["text"]:
                    updated_answer = re.sub(rf"\[{i+1}\]", f"[{global_id}]", updated_answer)
                    break
        return updated_answer

    def _process_sub_queries(self, sub_queries,subquery_answers,subq_source_nodes,citation_map):
        logger.info("updating ub query answers")
        for subquery in sub_queries:
            if subquery:
                subquery_answers[subquery] = self.remap_citations(
                    subquery_answers[subquery],
                    subq_source_nodes[subquery],
                    citation_map
                )
        return subquery_answers
    
    def _inputs_for_process_cntxt(self,citation_map):
        sources_text = "\n".join(
            [f"{v['text']}" for v in citation_map.values()]
        )
        return sources_text

    # def _inputs_for_process_cntxt(self,citation_map):
    #     sources_text = "\n".join(
    #         [f"[{k}] ({v['doc_name']}, Page {v['page_num']}): {v['text'][:300]}..." for k, v in citation_map.items()]
    #     )
    #     return sources_text

    # def _chat_synthesize_response(self, main_qb:str, subquery_results:List):

    #     chat_synthesize_prompt = self._prompts.chat_synthesizer.format(query=main_qb,combined_text = subquery_results)
    #     response_synth = get_response_synthesizer(
    #         response_mode="compact",
    #         text_qa_template=chat_synthesize_prompt,
    #         llm=self._model_manager.llm
    #     )

    #     subq_nodes = [NodeWithScore(node=TextNode(text=chunk)) for chunk in subquery_results]
    #     # subq_nodes = [TextNode(text=chunk) for chunk in subquery_results]

    #     response = response_synth.synthesize(main_qb, nodes=subq_nodes)
    #     # response = self._model_manager.llm.complete(
    #     #         self._prompts.report_summarizer.format(query=main_query,combined_text = subquery_results)
    #     #     )
    #     return response
    
    # def synthesize_markdown_report(self, main_query:str, subquery_results:List):
    #     response = self._model_manager.llm.complete(
    #             self._prompts.report_summarizer.format(query=main_query, combined_text = subquery_results)
    #         )
    #     return response
    
    def _synthesize_markdown_report_v2(self, main_query:str, subquery_answers:Dict, sources_text:List, first_pass_answer):
        subquery_answers_text = "\n\n".join(
            [f"Subquery {i+1}: {subquery}\nAnswer: {subquery_answers[subquery]}" 
            for i, subquery in enumerate(subquery_answers)]
        )
        subquery_answers_text += f"Main_query: {main_query}\nAnswer: {first_pass_answer}"
        logger.debug(f"synthesizing report, {subquery_answers_text}")
        response = self._model_manager.llm.complete(
                self._prompts.report_summarizer.format(query=main_query,sources_text = sources_text, subquery_answers_text = subquery_answers_text)
            )
        return response
    
    def _chat_synthesize_subanswers(self, main_query:str, subquery_results:List):
        response = self._model_manager.llm.complete(
                self._prompts.chat_synthesizer.format(query=main_query,subquery_results = subquery_results)
            )
        return response
    
    def _chat_synthesize_subanswers_v2(self, main_query:str, subquery_answers:Dict,sources_text:List):
        logger.info(f"synthesizing report")
        subquery_answers_text = "\n\n".join(
            [f"Subquery {i+1}: {subquery}\nAnswer: {subquery_answers[subquery]}" 
            for i, subquery in enumerate(subquery_answers)]
        )
        response = self._model_manager.llm.complete(
                self._prompts.chat_synthesizer_v2.format(query=main_query,sources_text = sources_text, subquery_answers_text = subquery_answers_text)
            )
        # response = self._model_manager.llm.complete(
        #         self._prompts.chat_synthesizer.format(query=main_query,subquery_results = subquery_results)
        #     )
        return response
    
    def response_generator(self, response_str, chunk_size=50):
        for i in range(0, len(response_str), chunk_size):
            chunk = response_str[i : i + chunk_size]
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "tokens",
                "text": chunk,
            })

    def _is_compound_query(self, query: str) -> bool:
        is_compound_prompt = self._prompts.is_compound_prompt.format(query=query)
        resp = self._model_manager.llm.complete(is_compound_prompt)
        return "yes" in resp.text.lower()
    
    def _parse_subqueries(self, llm_output: str) -> list[str]:
        try:
            return json.loads(llm_output)
        except json.JSONDecodeError:
            raise ValueError(f"Subquery output is not valid JSON:\n{llm_output}")

    def _decompose_query(self, query: str) -> List[str]:
        try:
            chat_sub_query_prompt = self._prompts.chat_subquery.format(query =query)
            response = self._model_manager.llm.complete(chat_sub_query_prompt).text.strip()
            subqueries = self._parse_subqueries(response)
            if isinstance(subqueries, list) and all(isinstance(q, str) for q in subqueries):
                return subqueries
            else:
                raise ValueError("Invalid format: not a list of strings")
        except json.JSONDecodeError as e:
            raise ValueError(f"Subquery response not valid JSON: {e}")

    # Convert citation_map into ordered retrieved_docs list
    def _ordered_docs(self,citation_map,subquery_docs,subquery_nodes):
        logger.info(f"ordering docs and nodes")
        # logger.info(f"sub query nodes {subquery_nodes}")
        extract_pattern = r"^Source \d+:\s*\n"
        ordered_docs = []
        ordered_nodes = []
        try:
            for citation_id in sorted(citation_map.keys(), key=int):  # Ensures 1,2,3...
                text = citation_map[citation_id]["text"]
                logger.debug(f"citation map text, {text}")
                for docs in subquery_docs.values():
                    for doc in docs:
                        if doc.text.strip() == text:
                            ordered_docs.append(doc)
                            break
                for nodes in subquery_nodes.values():
                    for node in nodes:
                        source_text = re.sub(
                            extract_pattern, "", node.node.get_text(), flags=re.MULTILINE
                        ).strip()
                        logger.debug(f"node text, {source_text}")
                        if source_text == text:
                            ordered_nodes.append(node)
                            break
            # logger.info(f"ordered nodes {ordered_nodes}")
            return ordered_docs, ordered_nodes
        except Exception as e:
            return ordered_docs, ordered_nodes

    async def _process_contexts(
        self, answer: str, source_nodes: List[Node], retrieved_docs: List[Node]
    ) -> Dict[str, Dict[str, Any]]:
        """Process and format context information from retrieved documents."""
        try:
            logger.info("Processing context information...")
            extract_pattern = r"^Source \d+:\s*\n"
            cited_nums = re.findall(r"\[(\d+)\]", answer)
            source_lst = []

            for source in source_nodes:
                logger.debug(f"source text, {source.node.get_text()}")
                source_text = re.sub(
                    extract_pattern, "", source.node.get_text(), flags=re.MULTILINE
                ).strip()
                source_lst.append(source_text)
            
            # logger.info(f"sources_list, {source_lst}")

            logger.debug(f"cited_nums, {cited_nums}")

            logger.debug(f"got {len(source_lst)} sources")
            contexts = {}
            retrieved_counter = 0

            for idx, doc in enumerate(retrieved_docs):
                if str(idx + 1) not in cited_nums:
                    logger.debug(f"{str(idx+1)} not in {cited_nums}")
                    continue
                
                if doc.text.strip() in source_lst:
                    retrieved_counter += 1
                    contexts[str(retrieved_counter)] = {
                        "doc_name": doc.metadata["doc_name"],
                        "page_num": doc.metadata["page_number"],
                        # "chunk": doc.metadata["highlighted_chunk"],
                    }
                    answer = answer.replace(
                        f"[{str(idx+1)}]",
                        f'[[{retrieved_counter}]](<{doc.metadata["s3_url"]}>)',
                    )
            logger.debug(f"Processed {contexts} context ")
            # logger.info(f"Processed {answer} answer ")
            return contexts, answer

        except Exception as e:
            logger.error(f"Error processing contexts: {e}")
            raise e
        
    async def _yield_context_answer(self, contexts, answer):
        logger.info(f"yielding contexts, {contexts}")
        logger.debug(f"answer yielding, {answer}")
        yield json.dumps({
            "response_id": str(uuid.uuid4()),
            "type": "answer",
            "text": answer
        })
        yield json.dumps({
            "response_id": str(uuid.uuid4()),
            "type": "context",
            "text": json.dumps(contexts),
        })

    async def _get_related_queries(self, response, answer):
        
        firstfivesources = "\n\n".join(doc.node.get_text() for doc in response.source_nodes[:5])  
        logger.info("generation of related queries started")
        related_queries = self._model_manager.llm.complete(
            self._prompts.related_queries_template.format(
                query=self._query,
                sources=firstfivesources,
                answer=answer,
            ),max_tokens=512
        ).text.strip()

        yield json.dumps({
            "response_id": str(uuid.uuid4()),
            "type": "related",
            "text": related_queries,
        })
        logger.info("generation of related queries ended")
    
    async def _generate_conversation_title(self):
        try:
            logger.debug("Generating conversation title...")
            conversation_title = self._model_manager.llm.complete(
                self._prompts.conv_title_template.format(
                    query=self._query, category=self._category_name
                )
            ).text.strip()

            logger.info("conversation title generated")
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "title",
                "text": conversation_title,
            })
        except:
            logger.error(f"Failed to generate conversation title: {e}")
            yield json.dumps({
                "response_id": str(uuid.uuid4()),
                "type": "title",
                "text": "Untitled Conversation"
            })
