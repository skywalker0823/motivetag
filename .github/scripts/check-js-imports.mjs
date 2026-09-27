// Fails when a browser module imports a file that is not in the repository.
// CI checks out only committed files, so a module missing from git (for example
// hidden by .gitignore) shows up here instead of as a 404 in production.
import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const files = execSync("git ls-files 'static/js/*.js'", { encoding: "utf8" }).split("\n").filter(Boolean);
const importPattern = /(?:import|export)\s[^"']*?from\s*["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g;
let missing = 0;

for (const file of files) {
  for (const match of readFileSync(file, "utf8").matchAll(importPattern)) {
    const spec = match[1] ?? match[2];
    let target;
    if (spec.startsWith("/")) target = join("static", spec);
    else if (spec.startsWith(".")) target = resolve(dirname(file), spec);
    else continue; // bare specifiers are not used without a bundler
    if (!existsSync(target)) {
      console.error(`${file}: imports ${spec}, which is not in the repository`);
      missing += 1;
    }
  }
}

console.log(`checked ${files.length} modules`);
process.exit(missing ? 1 : 0);
