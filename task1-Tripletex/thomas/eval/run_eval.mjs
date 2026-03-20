/**
 * Eval runner for Tier 1 cases.
 *
 * Usage:
 *   node thomas/eval/run_eval.mjs                      # run all
 *   node thomas/eval/run_eval.mjs --category employee   # filter by category
 *   node thomas/eval/run_eval.mjs --lang de             # filter by language
 *   node thomas/eval/run_eval.mjs --id t1_employee_01_nb # run single case
 *   node thomas/eval/run_eval.mjs --limit 5             # run first N
 */

import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";
import { config } from "dotenv";

const __dirname = dirname(fileURLToPath(import.meta.url));
const thomasDir = resolve(__dirname, "..");
const rootDir = resolve(thomasDir, "..");

config({ path: resolve(rootDir, ".env") });

const BASE_URL = process.env.TRIPLETEX_BASE_URL;
const TOKEN = process.env.TRIPLETEX_SESSION_TOKEN;

if (!BASE_URL || !TOKEN) {
  console.error("Missing TRIPLETEX_BASE_URL or TRIPLETEX_SESSION_TOKEN in .env");
  process.exit(1);
}

// Parse args
const args = process.argv.slice(2);
function getArg(name) {
  const i = args.indexOf(`--${name}`);
  return i !== -1 ? args[i + 1] : null;
}
const filterCategory = getArg("category");
const filterLang = getArg("lang");
const filterId = getArg("id");
const limit = getArg("limit") ? parseInt(getArg("limit")) : null;

// Load cases
let cases = readFileSync(resolve(__dirname, "tier1_cases.jsonl"), "utf-8")
  .trim()
  .split("\n")
  .map((l) => JSON.parse(l));

if (filterId) cases = cases.filter((c) => c.id === filterId);
if (filterCategory) cases = cases.filter((c) => c.category === filterCategory);
if (filterLang) cases = cases.filter((c) => c.lang === filterLang);
if (limit) cases = cases.slice(0, limit);

console.log(`Running ${cases.length} eval cases\n`);

// Helper: query sandbox API
function apiGet(path, params = "") {
  const url = `${BASE_URL}${path}?fields=*${params ? "&" + params : ""}`;
  const result = execSync(`curl -s -u "0:${TOKEN}" "${url}"`, {
    encoding: "utf-8",
  });
  return JSON.parse(result);
}

// Helper: check if field matches (case-insensitive for strings)
function fieldMatches(actual, expected) {
  if (actual === expected) return true;
  if (typeof actual === "string" && typeof expected === "string") {
    return actual.toLowerCase() === expected.toLowerCase();
  }
  if (typeof expected === "number") {
    return Number(actual) === expected;
  }
  if (typeof expected === "boolean") {
    return actual === expected;
  }
  return false;
}

// Verify results against sandbox
function verify(caseData) {
  const checks = caseData.expected_checks;
  const fields = checks.fields;
  const category = caseData.category;
  const results = { passed: [], failed: [], total: 0 };

  // Map category to API path
  const pathMap = {
    employee: "/employee",
    customer: "/customer",
    product: "/product",
    department: "/department",
    contact: "/contact",
  };

  const searchPath = pathMap[category];
  if (!searchPath) {
    results.failed.push(`Unknown category: ${category}`);
    return results;
  }

  try {
    const response = apiGet(searchPath);
    const entities = response.values || [];

    // Find the entity that best matches expected fields
    let bestMatch = null;
    let bestScore = 0;

    for (const entity of entities) {
      let score = 0;
      for (const [key, expected] of Object.entries(fields)) {
        if (fieldMatches(entity[key], expected)) score++;
      }
      if (score > bestScore) {
        bestScore = score;
        bestMatch = entity;
      }
    }

    results.total = Object.keys(fields).length;

    if (!bestMatch) {
      results.failed.push(`No ${category} entity found`);
      for (const key of Object.keys(fields)) {
        results.failed.push(`${key}: MISSING`);
      }
      return results;
    }

    // Check each expected field
    for (const [key, expected] of Object.entries(fields)) {
      // Special case: isAdministrator checks entitlements
      if (key === "isAdministrator" && expected === true && category === "employee") {
        try {
          const entResp = apiGet("/employee/entitlement", `employeeId=${bestMatch.id}`);
          const ents = entResp.values || [];
          // If they have entitlements beyond basic, they're an admin
          const hasEntitlements = ents.length > 0;
          // Also check userType
          const isExtended = bestMatch.userType === "EXTENDED";
          if (hasEntitlements || isExtended) {
            results.passed.push(`isAdministrator: true (entitlements granted or EXTENDED) ✓`);
          } else {
            results.failed.push(`isAdministrator: expected admin, userType="${bestMatch.userType}", entitlements=${ents.length}`);
          }
        } catch (e) {
          results.failed.push(`isAdministrator: could not check entitlements: ${e.message}`);
        }
        continue;
      }

      const actual = bestMatch[key];
      if (fieldMatches(actual, expected)) {
        results.passed.push(`${key}: "${actual}" ✓`);
      } else {
        results.failed.push(
          `${key}: expected "${expected}", got "${actual ?? "MISSING"}"`
        );
      }
    }
  } catch (e) {
    results.failed.push(`API error: ${e.message}`);
  }

  return results;
}

// Delete test data between runs
function cleanup(category) {
  // We don't delete — sandbox accumulates. Verification searches by field match.
}

// Run a single case
async function runCase(caseData) {
  const prompt = `
You have access to a Tripletex accounting API via curl.

Credentials (use these in your curl commands):
  BASE_URL="${BASE_URL}"
  SESSION_TOKEN="${TOKEN}"

Authentication: Basic Auth with username "0" and session token as password:
  curl -u "0:${TOKEN}" "${BASE_URL}/..."

Complete this accounting task by executing the actual API calls:

${caseData.prompt}

Execute the curl commands using Bash. After each call, check the response.
`;

  const instance = query({
    prompt,
    options: {
      model: "claude-haiku-4-5-20251001",
      permissionMode: "bypassPermissions",
      allowDangerouslySkipPermissions: true,
      cwd: thomasDir,
      settingSources: ["project"],
      allowedTools: ["Skill", "Read", "Bash"],
    },
  });

  // Consume output silently
  for await (const message of instance) {
    // silent
  }
}

// Main
const results = [];
let passed = 0;
let failed = 0;

for (let i = 0; i < cases.length; i++) {
  const c = cases[i];
  const label = `[${i + 1}/${cases.length}] ${c.id}`;
  process.stdout.write(`${label} ... `);

  try {
    await runCase(c);

    // Small delay for API consistency
    await new Promise((r) => setTimeout(r, 1000));

    const verification = verify(c);
    const passCount = verification.passed.length;
    const totalChecks = passCount + verification.failed.length;
    const score = totalChecks > 0 ? passCount / totalChecks : 0;

    const status = verification.failed.length === 0 ? "PASS" : "PARTIAL";
    const icon = status === "PASS" ? "✓" : "✗";

    console.log(
      `${icon} ${status} (${passCount}/${totalChecks} checks, score: ${score.toFixed(2)})`
    );

    if (verification.failed.length > 0) {
      for (const f of verification.failed) {
        console.log(`    FAIL: ${f}`);
      }
    }

    results.push({
      id: c.id,
      category: c.category,
      lang: c.lang,
      status,
      score,
      passed: verification.passed,
      failed: verification.failed,
    });

    if (status === "PASS") passed++;
    else failed++;
  } catch (e) {
    console.log(`✗ ERROR: ${e.message}`);
    results.push({
      id: c.id,
      category: c.category,
      lang: c.lang,
      status: "ERROR",
      score: 0,
      error: e.message,
    });
    failed++;
  }
}

// Summary
console.log(`\n${"=".repeat(60)}`);
console.log(`RESULTS: ${passed} passed, ${failed} failed out of ${cases.length}`);
console.log(`Pass rate: ${((passed / cases.length) * 100).toFixed(1)}%`);

// By category
const byCat = {};
for (const r of results) {
  if (!byCat[r.category]) byCat[r.category] = { pass: 0, fail: 0 };
  if (r.status === "PASS") byCat[r.category].pass++;
  else byCat[r.category].fail++;
}
console.log(`\nBy category:`);
for (const [cat, counts] of Object.entries(byCat)) {
  const total = counts.pass + counts.fail;
  console.log(
    `  ${cat}: ${counts.pass}/${total} (${((counts.pass / total) * 100).toFixed(0)}%)`
  );
}

// By language
const byLang = {};
for (const r of results) {
  if (!byLang[r.lang]) byLang[r.lang] = { pass: 0, fail: 0 };
  if (r.status === "PASS") byLang[r.lang].pass++;
  else byLang[r.lang].fail++;
}
console.log(`\nBy language:`);
for (const [lang, counts] of Object.entries(byLang)) {
  const total = counts.pass + counts.fail;
  console.log(
    `  ${lang}: ${counts.pass}/${total} (${((counts.pass / total) * 100).toFixed(0)}%)`
  );
}

// Save results
const resultsPath = resolve(__dirname, "results.json");
const fs = await import("fs");
fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
console.log(`\nDetailed results saved to: thomas/eval/results.json`);
