import logging
from enum import Enum
import json
from typing import Dict, List, Optional, Tuple, cast
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import QueryBundle, NodeWithScore
# from llama_index.core.constants import FUSION_MODES
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.postprocessor.cohere_rerank import CohereRerank
# from llama_index.core.postprocessor.types import TopKPostprocessor

logger = logging.getLogger(__name__)


class FUSION_MODES(str, Enum):
    """Enum for different fusion modes."""

    RECIPROCAL_RANK = "reciprocal_rerank"  # apply reciprocal rank fusion
    RELATIVE_SCORE = "relative_score"  # apply relative score fusion
    DIST_BASED_SCORE = "dist_based_score"  # apply distance-based score fusion
    SIMPLE = "simple"  # simple re-ordering of results based on original scores


class CompoundQueryRetrieverReport(QueryFusionRetriever):
    def __init__(self, compound_query_classify_prompt: str, node_postprocessors: List[BaseNodePostprocessor], report_subquery_gen_prompt: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compound_query_classify_prompt = compound_query_classify_prompt
        self._node_postprocessors = node_postprocessors
        self.report_subquery_gen_prompt = report_subquery_gen_prompt

    async def _is_compound_query(self, query: str) -> bool:
        is_compound_prompt = self.compound_query_classify_prompt.format(query=query)
        resp = await self._llm.acomplete(is_compound_prompt)
        return "yes" in resp.text.lower()

    def _parse_subqueries(self, llm_output: str) -> list[str]:
        try:
            return json.loads(llm_output)
        except json.JSONDecodeError:
            raise ValueError(f"Subquery output is not valid JSON:\n{llm_output}")

    async def _decompose_query(self, query: str) -> List[str]:
        try:
            sub_query_gen_prompt = self.query_gen_prompt.format(query =query)
            response = await self._llm.acomplete(sub_query_gen_prompt)
            subqueries = self._parse_subqueries(response.text)
            if isinstance(subqueries, list) and all(isinstance(q, str) for q in subqueries):
                return subqueries
            else:
                raise ValueError("Invalid format: not a list of strings")
        except json.JSONDecodeError as e:
            raise ValueError(f"Subquery response not valid JSON: {e}")
    
    def _combine_queries(self, compoundq_sub_queries: List[str], report_sub_questions: List[str]) -> List[str]:
        """Combine compound query sub-queries and deep research sub-queries."""
        combined_queries = []
        if compoundq_sub_queries:
            combined_queries.extend(compoundq_sub_queries)
        if report_sub_questions:
            combined_queries.extend(report_sub_questions)
        return combined_queries

    async def _gen_report_sub_questions(self, query: str, retrieved_docs) -> str:
        """Generate a deep research question based on the original query and retrieved documents."""
        # Use the query_gen_prompt to generate a deep research question
        # This prompt should be designed to take the original query and retrieved documents
        # and return a more focused question for deep research.
        # Example prompt:
        # "Given the original query: '{query}' and the retrieved documents: {retrieved_docs}, generate a deep research question that focuses on the most relevant aspects of the query."
        # Note: The retrieved_docs should be formatted as a string or list of strings.
        # This is a placeholder implementation; you should replace it with your actual logic.
        # Assuming retrieved_docs is a list of NodeWithScore objects, we can format them as
        # a string for the prompt.
        report_sub_questions = await self._llm.acomplete(
            self.report_subquery_gen_prompt.format(query=query, retrieved_docs=retrieved_docs)
        )
        return self._parse_subqueries(report_sub_questions.text)

    async def _compound_query_retrieval(self, query_bundle: QueryBundle)-> List[NodeWithScore]:
        return self._aretrieve(query_bundle)

    async def _get_queries(self, original_query: str) -> List[QueryBundle]:
        # Check if the query is compound
        subqueries = []
        if await self._is_compound_query(original_query):
            subqueries = await self._decompose_query(original_query)
        # The LLM often returns more queries than we asked for, so trim the list.
        logger.info(f"Subqueries: {subqueries}")
        return [QueryBundle(q) for q in subqueries[: self.num_queries - 1]]

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self.compound_query_bundle: List[QueryBundle] = []
        queries: List[QueryBundle] = [query_bundle]
        if self.num_queries > 1:
            queries.extend(self._get_queries(query_bundle.query_str))
        self.compound_query_bundle = queries
        if self.use_async:
            results = self._run_nested_async_queries(queries)
        else:
            results = self._run_sync_queries(queries)

        if self.mode == FUSION_MODES.RECIPROCAL_RANK:
            return self._reciprocal_rerank_fusion(results)[: self.similarity_top_k]
        elif self.mode == FUSION_MODES.RELATIVE_SCORE:
            return self._relative_score_fusion(results)[: self.similarity_top_k]
        elif self.mode == FUSION_MODES.DIST_BASED_SCORE:
            return self._relative_score_fusion(results, dist_based=True)[
                : self.similarity_top_k
            ]
        elif self.mode == FUSION_MODES.SIMPLE:
            return self._simple_fusion(results)[: self.similarity_top_k]
        else:
            raise ValueError(f"Invalid fusion mode: {self.mode}")
            
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self.compound_query_bundle: List[QueryBundle] = []
        queries: List[QueryBundle] = [query_bundle]
        if self.num_queries > 1:
            queries.extend(await self._get_queries(query_bundle.query_str))
        self.compound_query_bundle = queries
        results = await self._run_async_queries(queries)

        if self.mode == FUSION_MODES.RECIPROCAL_RANK:
            return self._reciprocal_rerank_fusion(results)[: self.similarity_top_k]
        elif self.mode == FUSION_MODES.RELATIVE_SCORE:
            return self._relative_score_fusion(results)[: self.similarity_top_k]
        elif self.mode == FUSION_MODES.DIST_BASED_SCORE:
            return self._relative_score_fusion(results, dist_based=True)[
                : self.similarity_top_k
            ]
        elif self.mode == FUSION_MODES.SIMPLE:
            return self._simple_fusion(results)[: self.similarity_top_k]
        else:
            raise ValueError(f"Invalid fusion mode: {self.mode}")
    
    # async def _run_report_queries(self, query_bundle_list: [QueryBundle]) -> List[NodeWithScore]:
    #     queries: List[QueryBundle] = query_bundle_list

    #     results = await self._run_async_queries(queries)

    #     if self.mode == FUSION_MODES.RECIPROCAL_RANK:
    #         return self._reciprocal_rerank_fusion(results)[: self.similarity_top_k]
    #     elif self.mode == FUSION_MODES.RELATIVE_SCORE:
    #         return self._relative_score_fusion(results)[: self.similarity_top_k]
    #     elif self.mode == FUSION_MODES.DIST_BASED_SCORE:
    #         return self._relative_score_fusion(results, dist_based=True)[
    #             : self.similarity_top_k
    #         ]
    #     elif self.mode == FUSION_MODES.SIMPLE:
    #         return self._simple_fusion(results)[: self.similarity_top_k]
    #     else:
    #         raise ValueError(f"Invalid fusion mode: {self.mode}")


    async def _run_report_queries(self, query_bundle_list: List[QueryBundle]) -> List[NodeWithScore]:
        # Run async queries → returns dict of (query, retriever_idx) -> List[NodeWithScore]
        results_dict: Dict[Tuple[str, int], List[NodeWithScore]] = await self._run_async_queries(query_bundle_list)

        # filtered_per_query: List[List[NodeWithScore]] = []
        fusion_input: Dict[Tuple[str, int], List[NodeWithScore]] = {}


        for (query_str, retriever_idx), result in results_dict.items():
            logger.info(f"Processing results for query: '{query_str}' from retriever {retriever_idx}")

            # Filter out invalid nodes
            nodes = [n for n in result if hasattr(n, "node")]

            # Apply per-query postprocessors
            for postprocessor in self._node_postprocessors:
                nodes = postprocessor.postprocess_nodes(nodes, query_bundle=QueryBundle(query_str))

            # # fusion_input[(query_str, retriever_idx)] = nodes
            # # TODO: Add similarity cut_off filtering here if needed
            # if self._config("RAG_SIMILARITY_CUTOFF") is not None:
                # nodes = [n for n in nodes if n.score > self._config("RAG_SIMILARITY_CUTOFF")]
            # nodes = [n for n in nodes if n.score > 0.3]
            fusion_input[(query_str, retriever_idx)] = nodes
        logger.info(f"Fusion input: {fusion_input}")
        # === FUSION STEP ===
        # You can switch to relative_score or dist_based by changing the method below
        if self.mode == FUSION_MODES.RECIPROCAL_RANK:
            fused_nodes = self._reciprocal_rerank_fusion(fusion_input)
        elif self.mode == FUSION_MODES.RELATIVE_SCORE:
            fused_nodes = self._relative_score_fusion(fusion_input)
        elif self.mode == FUSION_MODES.DIST_BASED_SCORE:
            fused_nodes = self._relative_score_fusion(fusion_input, dist_based=True)
        elif self.mode == FUSION_MODES.SIMPLE:
            fused_nodes = self._simple_fusion(fusion_input)
        else:
            raise ValueError(f"Invalid fusion mode: {self.mode}")

        # fused_nodes = fused_nodes[: self.similarity_top_k]
        fused_nodes = fused_nodes[:35]

        # for postprocessor in self._node_postprocessors:
        #     # Apply only reranker not similarity preprocessor
        #     if isinstance(postprocessor, CohereRerank):
        #         reranked_fusion_nodes = postprocessor.postprocess_nodes(fused_nodes, query_bundle=QueryBundle(query_str))
        # logger.info(f"Final fused nodes: {[n.node.get_content()[:100] for n in fused_nodes]}")
        # logger.info(f"Final reranked nodes: {[n.node.get_content()[:100] for n in reranked_fusion_nodes]}")
        return fused_nodes

    
    # # Applies TopKPostprocessor per query result and fuses them
    # async def _run_report_queries(self, query_bundle_list: List[QueryBundle]) -> List[NodeWithScore]:
    #     results_dict: Dict[Tuple[str, int], List[NodeWithScore]] = await self._run_async_queries(query_bundle_list)
    #     # logger.info(f"Raw results dict: {results_dict}")

    #     filtered_per_query: List[List[NodeWithScore]] = []

    #     for (query_str, retriever_idx), result in results_dict.items():
    #         logger.info(f"Processing results for query: '{query_str}' from retriever {retriever_idx}")
            
    #         # Filter out invalid nodes
    #         filtered_nodes = [n for n in result if hasattr(n, "node")]
    #         nodes = filtered_nodes

    #         # Apply all postprocessors to each result set
    #         for postprocessor in self._node_postprocessors:
    #             nodes = postprocessor.postprocess_nodes(nodes, query_bundle=QueryBundle(query_str))

    #         filtered_per_query.append(nodes)

    #     # Flatten all processed results for final fusion/ranking
    #     all_nodes_flat: List[NodeWithScore] = [node for group in filtered_per_query for node in group]
    #     logger.info(f"Final flattened nodes after postprocessing: {all_nodes_flat}")
    #     return all_nodes_flat

    #     # # Apply fusion
    #     # if self.mode == FUSION_MODES.RECIPROCAL_RANK:
    #     #     return self._reciprocal_rerank_fusion(filtered_per_query)[: self.similarity_top_k]
    #     # elif self.mode == FUSION_MODES.RELATIVE_SCORE:
    #     #     return self._relative_score_fusion(filtered_per_query)[: self.similarity_top_k]
    #     # elif self.mode == FUSION_MODES.DIST_BASED_SCORE:
    #     #     return self._relative_score_fusion(filtered_per_query, dist_based=True)[: self.similarity_top_k]
    #     # elif self.mode == FUSION_MODES.SIMPLE:
    #     #     return self._simple_fusion(filtered_per_query)[: self.similarity_top_k]
    #     # else:
    #     #     raise ValueError(f"Invalid fusion mode: {self.mode}")

    async def _aretrieve_report(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self.report_query_bundle: List[QueryBundle] = []
        orig_nodes = await self._compound_query_retrieval(query_bundle)
        logger.info(f"Original nodes: {orig_nodes}")
        report_sub_questions = await self._gen_report_sub_questions(
            query_bundle.query_str, orig_nodes
        )
        logger.info(f"Report sub-questions: {report_sub_questions}")

        combined_queries_bundle = [query_bundle]
        combined_queries_bundle.extend([QueryBundle(q) for q in report_sub_questions])
        logger.info(f"Combined queries: {combined_queries_bundle}")
        self.report_query_bundle = combined_queries_bundle
        return await self._run_report_queries(combined_queries_bundle) 

    async def get_report_subqueries(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self.report_query_bundle: List[QueryBundle] = []
        orig_nodes = await self._compound_query_retrieval(query_bundle)
        logger.info(f"Original nodes: {orig_nodes}")
        report_sub_questions = await self._gen_report_sub_questions(
            query_bundle.query_str, orig_nodes
        )
        logger.info(f"Report sub-questions: {report_sub_questions}")

        combined_queries_bundle = [query_bundle]
        combined_queries_bundle.extend([QueryBundle(q) for q in report_sub_questions])
        logger.info(f"Combined queries: {combined_queries_bundle}")
        self.report_query_bundle = combined_queries_bundle
        return self.report_query_bundle     
