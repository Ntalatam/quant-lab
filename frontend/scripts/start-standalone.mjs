import {
  cpSync,
  existsSync,
  mkdirSync,
  rmSync,
} from "node:fs";
import { resolve } from "node:path";
import { spawn } from "node:child_process";

function readArg(flag) {
  const index = process.argv.indexOf(flag);
  if (index === -1) return undefined;
  return process.argv[index + 1];
}

const hostname = readArg("--hostname") ?? process.env.HOSTNAME ?? "0.0.0.0";
const port = readArg("--port") ?? process.env.PORT ?? "3000";

const serverPath = resolve(".next/standalone/server.js");
const standaloneRoot = resolve(".next/standalone");
const standaloneNextDir = resolve(standaloneRoot, ".next");
const staticSource = resolve(".next/static");
const staticTarget = resolve(standaloneNextDir, "static");
const publicSource = resolve("public");
const publicTarget = resolve(standaloneRoot, "public");

if (!existsSync(serverPath)) {
  console.error(
    "Standalone build output was not found. Run `npm run build` before starting the standalone server."
  );
  process.exit(1);
}

if (!existsSync(staticSource)) {
  console.error(
    "Client static assets were not found. Run `npm run build` before starting the standalone server."
  );
  process.exit(1);
}

mkdirSync(standaloneNextDir, { recursive: true });
rmSync(staticTarget, { recursive: true, force: true });
cpSync(staticSource, staticTarget, { recursive: true });

if (existsSync(publicSource)) {
  rmSync(publicTarget, { recursive: true, force: true });
  cpSync(publicSource, publicTarget, { recursive: true });
}

const child = spawn(process.execPath, [serverPath], {
  stdio: "inherit",
  env: {
    ...process.env,
    HOSTNAME: hostname,
    PORT: String(port),
  },
});

const forwardSignal = (signal) => {
  if (!child.killed) {
    child.kill(signal);
  }
};

process.on("SIGINT", () => forwardSignal("SIGINT"));
process.on("SIGTERM", () => forwardSignal("SIGTERM"));

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
