import { cp, mkdir, rm, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(resolve(root, "app"), dist, { recursive: true });
await cp(resolve(root, "engine"), resolve(dist, "engine"), { recursive: true });

const appPath = resolve(dist, "app.js");
const app = await readFile(appPath, "utf8");
await writeFile(appPath, app.replace("../engine/index.js", "./engine/index.js"));
