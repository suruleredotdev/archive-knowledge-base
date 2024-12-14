import Arena from "are.na";
// const toolConfig = require("./tool-config.json");
import sqlite3 from "sqlite3";

const LOG_LEVEL = process.env.LOG_LEVEL || "INFO";

const ARENA_USER = {
  slug: "korede-aderele",
  id: 60392,
  token: process.env.ARENA_PERSONAL_ACCESS_TOKEN
};
const ARENA_CHANNELS: Array<string> = [
  "Stream",
  "Permaculture",
  "Historiography",
  "African Empires+States",
  "Yoruba History+Language+Religion",
  "Hausa History+Language+Religion",
  "Igbo History+Language+Religion",
  "Oral Tradition",
  "Nigeria History",
  "Nigeria Politics",
  "Maps",
  "Mutual Aid",
  "Startup"
];

const db = new sqlite3.Database(process.env.DB_PATH || "./store.sqlite3");
const arenaClient = new Arena({ accessToken: ARENA_USER.token });

async function saveArenaBlock(
  db: sqlite3.Database,
  {
    arenaBlockId,
    sourceUrl,
    fullJson,
    crawledText,
    title,
    description,
    metadata
  }: {
    arenaBlockId: string;
    sourceUrl: string;
    fullJson: string;
    crawledText: string;
    title: string;
    description: string;
    metadata: string;
  }
) {
  return await db.run(
    `INSERT INTO "block" (
      id,
      source_url,
      full_json,
      crawled_text,
      title,
      description,
      metadata
     ) VALUES (
      ?, ?, ?, ?, ?, ?, ?
     )
      ON CONFLICT (id)
      DO UPDATE SET
        source_url = excluded.source_url,
        full_json = excluded.full_json,
        crawled_text = excluded.crawled_text,
        title = excluded.title,
        description = excluded.description,
        metadata = excluded.metadata,
        updated_at = CURRENT_TIMESTAMP;`,
    [
      arenaBlockId,
      sourceUrl,
      fullJson,
      crawledText,
      title,
      description,
      metadata
    ]
  );
}

async function getArenaBlocks(
  arenaClient: Arena,
  {
    postNewBlocksSince,
    postNewBlocksTill
  }: {
    postNewBlocksSince: Date;
    postNewBlocksTill: Date;
  }
): Promise<Record<string, Arena.Block>> {
  const channels = await arenaClient.user(ARENA_USER.id).channels();
  if (LOG_LEVEL === "DEBUG") {
    console.log("ARENA channels resp", {
      length: channels?.length,
      titles: channels?.map(c => c.title),
      first: channels[0]
    });
  }

  const blocksToSync: Record<string, Arena.Block> = {};
  const allChannelNames = new Set();
  const blockChannelsMap: Record<string, Set<string>> = {};

  try {
    for (var i = 0; i < channels.length; i++) {
      const channel = channels[i];

      if (!ARENA_CHANNELS.includes(channel.title)) continue;

      if (LOG_LEVEL === "INFO") console.info(JSON.stringify(channel));
      if (!channel.contents) {
        if (LOG_LEVEL === "DEBUG") {
          console.log(`Skipping channel idx ${i} due to empty contents`);
        }
        continue;
      }

      for (var j = 0; j < channel.contents?.length; j++) {
        const block = channel.contents[j];

        // TODO: this should parse connections to the current channel
        let block_connected_date = new Date(block["created_at"]);

        if (LOG_LEVEL === "DEBUG") {
          console.log(
            `>>> considering block #${block.id} "${block.title}" to post,
          in date range
          SINCE:${postNewBlocksSince?.toLocaleString()} < ${block_connected_date?.toLocaleString()} <= TILL:${postNewBlocksTill?.toLocaleString()}`
          );
        }

        // block matched!
        if (
          block_connected_date > postNewBlocksSince &&
          block_connected_date <= postNewBlocksTill
        ) {
          if (LOG_LEVEL === "INFO") console.info(JSON.stringify(channel));
          blocksToSync[block.id] = block;
          if (block.id in blockChannelsMap) {
            blockChannelsMap[block.id].add(channel.title);
          } else {
            blockChannelsMap[block.id] = new Set([channel.title]);
          }
          allChannelNames.add(channel.title);
        }
      }

      if (LOG_LEVEL === "DEBUG") {
        console.log(">> blocks loop finish");
      }

      if (LOG_LEVEL === "DEBUG") {
        console.log({
          name: channel.title,
          blocks_preview: channel.contents
            ?.slice(0, 5)
            .map(block => block.title)
        });
      }
    }

    return blocksToSync;
  } catch (err) {
    console.error("ARENA ERR", err);
    return;
  }
}

async function runMain() {
  const args = {
    postNewBlocksSince: new Date("2024/01/01"),
    postNewBlocksTill: new Date()
  };
  if (LOG_LEVEL === "DEBUG") console.log("ARGS", args);
  const { postNewBlocksSince, postNewBlocksTill } = args;

  const blocks = await getArenaBlocks(arenaClient, {
    postNewBlocksSince,
    postNewBlocksTill
  });

  for (const [blockId, blockData] of Object.entries(blocks)) {
    await saveArenaBlock(db, {
      arenaBlockId: blockId,
      sourceUrl: blockData.source?.url,
      fullJson: JSON.stringify(blockData),
      crawledText: blockData.content,
      title: blockData.title,
      description: blockData.description,
      metadata: "" // figure this out later
    });
  }
}

runMain()
  .then(() => {
    console.log("done");
  })
  .catch(e => {
    console.log("error", e);
  });
