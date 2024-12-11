const Arena = require("are.na");
// const toolConfig = require("./tool-config.json");
const sqlite3 = require("sqlite3").verbose();

const LOG_LEVEL = process.env.LOG_LEVEL || "INFO";

const ARENA_USER = {
  slug: "korede-aderele",
  id: 60392,
  token: process.env.ARENA_PERSONAL_ACCESS_TOKEN,
};
const ARENA_CHANNELS = [
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
  "Startup",
];

const db = new sqlite3.Database(process.env.DB_PATH || "./store.sqlite3");
const arenaClient = new Arena({accessToken: ARENA_USER.token});

async function saveArenaBlock(db, {arenaBlockId, sourceUrl, fullJson}) {
  return await db.run(
    `INSERT INTO "block" (
      block_id,
      block_source_url,
      full_json
     ) VALUES (?, ?, ?)
      ON CONFLICT (block_id)
      DO UPDATE SET block_source_url = excluded.block_source_url,
        full_json = excluded.full_json,
        updated_at = DATE();`,
    [arenaBlockId, sourceUrl, fullJson]
  );
}

async function getArenaBlocks(arenaClient, {postNewBlocksSince, postNewBlocksTill}) {
  const channels = await arenaClient.user(ARENA_USER.id).channels();
  if (LOG_LEVEL === "DEBUG") {
    console.log("ARENA channels resp", {
      length: channels?.length,
      titles: channels?.map((c) => c.title),
      first: channels[0],
    });
  }

  const blocksToSync = {}; //: Record<string, Arena.Block>
  const allChannelNames = new Set();
  const blockChannelsMap = {}; // Map<String: block_id, Set<String>>

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

        let block_connected_date = new Date(
          Math.min.apply(null, [
            new Date(block["connected_at"]),
            new Date(block["connected_at"]),
          ])
        );

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
            .map((block) => block.title),
        });
      }
    }
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
  const {postNewBlocksSince, postNewBlocksTill} = args;

  await getArenaBlocks(arenaClient, {postNewBlocksSince, postNewBlocksTill})
}

runMain()
