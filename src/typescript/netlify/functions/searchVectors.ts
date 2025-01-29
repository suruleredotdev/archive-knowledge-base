import type { Context } from "@netlify/functions";

import { QdrantClient } from '@qdrant/js-client-rest';
import { HuggingFaceTransformersEmbeddings } from "@langchain/community/embeddings/huggingface_transformers";


export default async (req: Request, context: Context) => {
    const client = new QdrantClient({
        url: process.env.QDRANT_URL,
        apiKey: process.env.QDRANT_API_KEY,
    });
    const body = await req.json();

    if (!body) {
        return new Response("No body found", { status: 400 });
    }

    if (!body?.query) {
        return new Response("No query found", { status: 400 });
    }

    const query = body?.query;
    const limit = body?.limit ? parseInt(body.limit) : 10;

    console.log("QUERY", query);
    try {
        const embeddings = new HuggingFaceTransformersEmbeddings({
            model: "sentence-transformers/all-MiniLM-L6-v2",
        });
        const vector = await embeddings.embedQuery(query);
        const result = await client.query("arena_blocks", {
            query: {
                vector: vector
            },
            limit: limit,
            with_payload: true
        });
        console.log("RESULT", result);

        return new Response(JSON.stringify(result), { status: 200 });
    } catch (error) {
        console.error("ERROR", error, error.message, error.statusText, error.data);
        return new Response("Error", { status: 500 });
    }
}
