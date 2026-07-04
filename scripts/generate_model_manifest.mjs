import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(process.argv[2] ?? "Models");
const architectures = [
  {
    name: "MobileNetV2",
    directory: "MobilenetV2",
    inputShape: [128, 128, 3],
  },
  {
    name: "DenseNet121",
    directory: "DenseNet121",
    inputShape: [128, 128, 3],
  },
  {
    name: "InceptionV3",
    directory: "InceptionV3",
    inputShape: [299, 299, 3],
  },
];

function hashFile(filePath) {
  return new Promise((resolve, reject) => {
    const digest = createHash("sha256");
    const stream = createReadStream(filePath);
    stream.on("error", reject);
    stream.on("data", (chunk) => digest.update(chunk));
    stream.on("end", () => resolve(digest.digest("hex")));
  });
}

const artifacts = [];
for (const architecture of architectures) {
  const directoryPath = path.join(root, architecture.directory);
  const names = (await readdir(directoryPath))
    .filter((name) => /^model_[1-4][a-f]\.h5$/.test(name))
    .sort();

  for (const name of names) {
    const filePath = path.join(directoryPath, name);
    const fileStats = await stat(filePath);
    const code = name.match(/^model_([1-4])([a-f])\.h5$/);
    artifacts.push({
      architecture: architecture.name,
      section: `S-${code[1]}${code[2].toUpperCase()}`,
      path: path.posix.join(architecture.directory, name),
      size_bytes: fileStats.size,
      sha256: await hashFile(filePath),
      format: "keras-h5",
      input_shape: architecture.inputShape,
      preprocessing: "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255",
      version: "1",
    });
  }
}

if (artifacts.length !== 72) {
  throw new Error(`Expected 72 model artifacts, found ${artifacts.length}`);
}

const manifest = {
  schema_version: 1,
  generated_from: "local-artifacts",
  artifacts,
};
await writeFile(
  path.join(root, "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
  "utf8",
);
console.log(`Wrote ${artifacts.length} verified artifact records.`);
