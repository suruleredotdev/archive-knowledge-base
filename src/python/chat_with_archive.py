from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from vector_store import VectorStore
import argparse
import logging
import os
from typing import List, Dict
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGQueryEngine:
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.0,
        max_tokens: int = 500,
        vector_store: VectorStore = None
    ):
        """Initialize RAG query engine"""
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.vector_store = vector_store or VectorStore()
        
        # Setup RAG prompt
        template = """You are a helpful research assistant. Use the following retrieved documents to answer the question. 
If you cannot answer the question based on the documents, say so.

Retrieved documents:
{context}

Question: {question}

Answer the question in a clear and concise way. Include relevant quotes and citations from the source documents when appropriate.
Include the source URLs for any information you use in your response.

Answer:"""
        
        self.prompt = ChatPromptTemplate.from_template(template)
        
    def _format_docs(self, docs: List[Dict]) -> str:
        """Format retrieved documents into context string"""
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            formatted_docs.append(
                f"Document {i}:\n"
                f"Title: {doc['title']}\n"
                f"URL: {doc['source_url']}\n"
                f"Content: {doc['text_preview']}\n"
            )
        return "\n\n".join(formatted_docs)
        
    def retrieve(self, query: str, limit: int = 3) -> str:
        """Retrieve relevant documents"""
        results = self.vector_store.search(query, limit=limit)
        return self._format_docs(results)
        
    def query(self, question: str, limit: int = 3) -> str:
        """Run RAG query pipeline"""
        # Setup RAG chain
        rag_chain = (
            {"context": lambda x: self.retrieve(x, limit=limit), "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
        # Run chain
        return rag_chain.invoke(question)

def main():
    parser = argparse.ArgumentParser(description='Query vector store using RAG')
    parser.add_argument(
        'question',
        help='Question to ask'
    )
    parser.add_argument(
        '--model',
        default='gpt-3.5-turbo',
        help='OpenAI model to use (default: gpt-3.5-turbo)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=3,
        help='Number of documents to retrieve (default: 3)'
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.0,
        help='LLM temperature (default: 0.0)'
    )
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=500,
        help='Maximum tokens in response (default: 500)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--show-sources',
        action='store_true',
        help='Show retrieved sources before answer'
    )
    args = parser.parse_args()

    # Setup logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable not set")

    try:
        # Initialize RAG engine
        rag = RAGQueryEngine(
            model_name=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        
        # Show sources if requested
        if args.show_sources:
            print("\nRetrieved Sources:")
            print("-" * 50)
            print(rag.retrieve(args.question, args.limit))
            print("-" * 50)
        
        # Get answer
        print("\nQuestion:", args.question)
        print("\nThinking...\n")
        answer = rag.query(args.question, args.limit)
        print("Answer:", answer)
        
    except Exception as e:
        logger.error(f"Error during RAG query: {e}", exc_info=args.debug)
        raise

if __name__ == "__main__":
    main()