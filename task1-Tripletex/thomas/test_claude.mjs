import { query } from "@anthropic-ai/claude-agent-sdk";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";
import { readFileSync } from "fs";
import { config } from "dotenv";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectDir = resolve(__dirname);

// Load .env from task1-Tripletex root
config({ path: resolve(__dirname, "..", ".env") });

const BASE_URL = process.env.TRIPLETEX_BASE_URL;
const SESSION_TOKEN = process.env.TRIPLETEX_SESSION_TOKEN;

if (!BASE_URL || !SESSION_TOKEN) {
  console.error("Missing TRIPLETEX_BASE_URL or TRIPLETEX_SESSION_TOKEN in .env");
  process.exit(1);
}

const task = process.argv[2] || "Opprett en ansatt med navn Ola Nordmann og epostadresse ola@example.com.";

const prompt = `
You have access to a Tripletex accounting API via curl.

Credentials (already set as env vars you can use directly in bash):
  export BASE_URL="${BASE_URL}"
  export SESSION_TOKEN="${SESSION_TOKEN}"

Authentication: Basic Auth with username "0" and session token as password.
  curl -u "0:$SESSION_TOKEN" ...

Complete this accounting task by executing the actual API calls:

${task}

Execute the curl commands using Bash. After each call, check the response to verify it worked.
`;

console.log(`Task: ${task}\n`);

const instance = query({
  prompt,
  options: {
    model: "claude-haiku-4-5-20251001",
    permissionMode: "bypassPermissions",
    allowDangerouslySkipPermissions: true,
    cwd: projectDir,
    settingSources: ["project"],
    allowedTools: ["Skill", "Read", "Bash"],
  },
});

for await (const message of instance) {
  if (message.type === "assistant") {
    for (const block of message.message.content) {
      if (block.type === "text") {
        process.stdout.write(block.text);
      }
    }
  } else if (message.type === "result") {
    console.log("\n\n--- Done ---");
  }
}
