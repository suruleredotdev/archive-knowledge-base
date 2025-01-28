import argparse
import logging
from vector_store import VectorStore

def setup_logging(debug=False):
    """Configure logging level and format"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Search blocks using vector similarity')
    parser.add_argument(
        'query',
        help='Search query text'
    )
    parser.add_argument(
        '--limit', 
        type=int,
        default=5,
        help='Maximum number of results to return (default: 5)'
    )
    parser.add_argument(
        '--qdrant-host',
        help='Remote Qdrant host (if not specified, uses local storage)'
    )
    parser.add_argument(
        '--qdrant-port',
        type=int,
        help='Remote Qdrant port'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    # Initialize vector store
    vector_store = VectorStore(
        host=args.qdrant_host,
        port=args.qdrant_port
    )

    # Search for similar content
    results = vector_store.search(args.query, limit=args.limit)

    # Output results based on format
    if args.format == 'json':
        import json
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No results found.")
            return
            
        print(f"\nFound {len(results)} results for: '{args.query}'\n")
        for result in results:
            print(f"Score: {result['score']:.3f}")
            print(f"Title: {result['title']}")
            print(f"URL: {result['source_url']}")
            print(f"Preview: {result['text_preview'][:200]}...")
            print()

if __name__ == "__main__":
    main()