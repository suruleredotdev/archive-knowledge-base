import type { Context } from "@netlify/functions";

import { QdrantClient } from '@qdrant/js-client-rest';

export default async (req: Request, context: Context) => {
    const client = new QdrantClient({
        url: process.env.QDRANT_URL,
        apiKey: process.env.QDRANT_API_KEY,
    });
    const body = await req.json();

    if (!body) {
        return new Response("No body found", { status: 400 });
    }

    const offset = body?.offset ? parseInt(body.offset) : 0;
    const limit = body?.limit ? parseInt(body.limit) : 10;

    const query = body?.query;
    const with_vector = body?.with_vector ? body.with_vector : false;

    try {
        const result = await executeQueryOrScroll(client, query, offset, limit, with_vector);
        return new Response(JSON.stringify(result), { status: 200 });
    } catch (error) {
        console.error("ERROR", error, error.message, error.statusText, error.data);
        return new Response("Error", { status: 500 });
    }
}

async function executeQueryOrScroll(client: QdrantClient, query: any, offset: number, limit: number, with_vector: boolean) {
    if (query) {
        const result = await client.query("arena_blocks", {
            query:  query,
            limit: limit,
            with_payload: true,
            with_vector: with_vector,
        });

        return result;
    } else {
        const result = await client.scroll("arena_blocks", {
            offset: offset,
            limit: limit,
            with_payload: true,
            with_vector: with_vector,
        });

        return result;
    }
}