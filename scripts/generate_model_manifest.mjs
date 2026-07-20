import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const args = process.argv.slice(2);

function argument(name, fallback) {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}

const projectRoot = path.resolve(import.meta.dirname, "..");
const modelRoot = path.resolve(
  projectRoot,
  argument("--model-root", "Models_New"),
);
const trainingManifestPath = path.resolve(
  projectRoot,
  argument(
    "--training-manifest",
    "Models_New/training_manifest_export.json",
  ),
);
const trainingGoldenPath = path.resolve(
  projectRoot,
  argument("--training-golden", "Models_New/golden_inference.json"),
);
const outputPath = path.resolve(
  projectRoot,
  argument("--output", "Models_New/manifest.json"),
);
const fallbackOutputPath = path.resolve(
  projectRoot,
  argument("--fallback-output", "Models/manifest.json"),
);

const sectionScoreMap = {
  "1a": [1, 2, 3, 4],
  "1b": [0, 1, 2, 3, 4],
  "1c": [0, 1, 2, 3, 4],
  "1d": [0, 1, 2, 3, 4],
  "1e": [0, 1, 2, 3, 4],
  "1f": [0, 1, 2, 3, 4, 5],
  "2a": [0, 1, 2, 3, 4],
  "2b": [0, 1, 2, 4],
  "2c": [0, 1, 2, 3, 4],
  "2d": [0, 1, 2, 3, 4],
  "2e": [0, 1, 2, 3, 4],
  "2f": [0, 1, 2, 3, 4, 5],
  "3a": [0, 1, 2, 3, 4],
  "3b": [0, 1, 2, 3, 4],
  "3c": [0, 1, 2, 3, 4],
  "3d": [0, 1, 2, 3, 4],
  "3e": [0, 1, 2, 3, 4],
  "3f": [0, 1, 2, 3, 5],
  "4a": [0, 1, 2, 3, 4],
  "4b": [0, 1, 2, 3, 4],
  "4c": [0, 1, 2, 3, 4],
  "4d": [0, 1, 2, 3, 4],
  "4e": [0, 1, 2, 3, 4],
  "4f": [0, 1, 2, 3, 4, 5],
};

const sections = Object.keys(sectionScoreMap);
const architectures = [
  {
    name: "MobileNetV2",
    inputShape: [224, 224, 3],
    preprocessing:
      "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_MOBILENETV2_PREPROCESS_INPUT",
    applicationPreprocessing: "KERAS_MOBILENETV2_PREPROCESS_INPUT",
  },
  {
    name: "DenseNet121",
    inputShape: [224, 224, 3],
    preprocessing:
      "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_DENSENET121_PREPROCESS_INPUT",
    applicationPreprocessing: "KERAS_DENSENET121_PREPROCESS_INPUT",
  },
  {
    name: "InceptionV3",
    inputShape: [299, 299, 3],
    preprocessing:
      "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_INCEPTIONV3_PREPROCESS_INPUT",
    applicationPreprocessing: "KERAS_INCEPTIONV3_PREPROCESS_INPUT",
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

function assert(condition, code) {
  if (!condition) {
    throw new Error(code);
  }
}

function sameArray(left, right) {
  return (
    Array.isArray(left) &&
    Array.isArray(right) &&
    left.length === right.length &&
    left.every((value, index) => value === right[index])
  );
}

const trainingManifest = JSON.parse(
  await readFile(trainingManifestPath, "utf8"),
);
const trainingGolden = JSON.parse(await readFile(trainingGoldenPath, "utf8"));

const artifacts = [];
for (const architecture of architectures) {
  const manifestArchitecture = trainingManifest.models?.[architecture.name];
  const goldenArchitecture = trainingGolden.models?.[architecture.name];
  assert(manifestArchitecture, `training_manifest_missing:${architecture.name}`);
  assert(goldenArchitecture, `training_golden_missing:${architecture.name}`);

  for (const section of sections) {
    const manifestEntry = manifestArchitecture.sections?.[section];
    const goldenEntry = goldenArchitecture.sections?.[section];
    assert(
      manifestEntry,
      `training_manifest_section_missing:${architecture.name}:${section}`,
    );
    assert(
      goldenEntry,
      `training_golden_section_missing:${architecture.name}:${section}`,
    );

    const relativePath = path.posix.join(
      architecture.name,
      `model_${section}.h5`,
    );
    const filePath = path.join(modelRoot, relativePath);
    const fileStats = await stat(filePath);
    const sha256 = await hashFile(filePath);
    const expectedLabels = sectionScoreMap[section].map(String);
    const goldenInputShape = goldenEntry.input_shape?.slice(1);

    assert(
      fileStats.size === manifestEntry.file_size_bytes,
      `training_manifest_size_mismatch:${architecture.name}:${section}`,
    );
    assert(
      sha256 === manifestEntry.sha256,
      `training_manifest_hash_mismatch:${architecture.name}:${section}`,
    );
    assert(
      sha256 === goldenEntry.model_sha256,
      `training_golden_hash_mismatch:${architecture.name}:${section}`,
    );
    assert(
      goldenEntry.status === "success",
      `training_golden_failed:${architecture.name}:${section}`,
    );
    assert(
      sameArray(goldenInputShape, architecture.inputShape),
      `training_golden_input_shape_mismatch:${architecture.name}:${section}`,
    );
    assert(
      sameArray(goldenEntry.section_class_labels, expectedLabels),
      `class_mapping_mismatch:${architecture.name}:${section}`,
    );
    assert(
      goldenEntry.num_output_classes === expectedLabels.length &&
        goldenEntry.output_shape?.at(-1) === expectedLabels.length,
      `output_shape_mismatch:${architecture.name}:${section}`,
    );
    assert(
      Number.isInteger(goldenEntry.predicted_index) &&
        goldenEntry.predicted_index >= 0 &&
        goldenEntry.predicted_index < expectedLabels.length,
      `golden_predicted_index_invalid:${architecture.name}:${section}`,
    );

    artifacts.push({
      architecture: architecture.name,
      section: `S-${section.toUpperCase()}`,
      path: relativePath,
      size_bytes: fileStats.size,
      sha256,
      format: "keras-h5",
      input_shape: architecture.inputShape,
      output_shape: goldenEntry.output_shape,
      class_labels: expectedLabels,
      score_mapping_source: "services.class_mapping.CLASS_SCORE_MAP",
      dataset_preprocessing: "SECTION_BINARY_NON_INVERTED",
      application_preprocessing: architecture.applicationPreprocessing,
      preprocessing: architecture.preprocessing,
      runtime_color_mode: "rgb_from_binary_non_inverted",
      training_ratio: trainingManifest.ratio,
      source_training_path: manifestEntry.file_path,
      golden_sample_image_sha256: goldenEntry.sample_image_sha256,
      golden_predicted_index: goldenEntry.predicted_index,
      golden_confidence: goldenEntry.confidence,
    });
  }
}

assert(artifacts.length === 72, `expected_72_artifacts_found_${artifacts.length}`);

const artifactContractDigest = createHash("sha256")
  .update(
    JSON.stringify(
      artifacts.map(
        ({ architecture, section, sha256, input_shape, output_shape, class_labels }) => ({
          architecture,
          section,
          sha256,
          input_shape,
          output_shape,
          class_labels,
        }),
      ),
    ),
  )
  .digest("hex");

const generatedAt = new Date().toISOString();
const manifest = {
  schema_version: 2,
  manifest_type: "emathtoco-runtime-model-manifest",
  generated_at: generatedAt,
  generated_from:
    "Models_New training manifest, training golden inference, and local H5 checksums",
  source_training_manifest: path.basename(trainingManifestPath),
  source_golden_inference: path.basename(trainingGoldenPath),
  model_collection: "Models_New",
  model_release: "models-new-densenet-bn-policy-aligned-2026-07-19",
  total_artifacts: artifacts.length,
  expected_sections: sections.map((section) => `S-${section.toUpperCase()}`),
  artifact_contract_sha256: artifactContractDigest,
  training_dataset_path: trainingManifest.dataset_path,
  training_dataset_preprocessing: {
    decision_source: "verified_training_dataset_samples_2026-07-17",
    source_notebook_in_repo: "Models_New/Preprocessing.ipynb",
    preprocessing_notebook_status:
      "non_authoritative_polarity_mismatch_with_training_dataset_artifacts",
    evidence:
      "Verified training PNGs are binary black ink on white background. Training loaders use RGB mode and architecture-specific Keras preprocess_input.",
    steps: [
      "use the complete section crop produced by the frontend without a second contour crop",
      "convert to grayscale and apply non-inverted Otsu binary threshold",
      "replicate the binary image across three RGB channels",
      "resize with nearest-neighbor interpolation to the architecture input shape",
      "apply the matching Keras application preprocess_input function",
    ],
  },
  runtime_policy: {
    no_frontend_flow_change: true,
    model_root_switchable: true,
    recommended_default_architecture: "MobileNetV2",
    exactly_one_rq_worker: true,
    manifest_required_for_readiness: true,
  },
  architecture_comparison_policy: {
    shared_classification_head_protocol: true,
    shared_batch_normalization_policy: true,
    backbone_architectures_are_identical: false,
    note:
      "The three backbones remain architecturally different. Comparable means the fine-tuning, BatchNormalization freeze policy, head protocol, split, and optimization settings are aligned; it does not mean identical layer counts.",
  },
  architectures: Object.fromEntries(
    architectures.map((architecture) => [
      architecture.name,
      {
        input_shape: architecture.inputShape,
        preprocessing: architecture.preprocessing,
        total_sections: sections.length,
      },
    ]),
  ),
  artifacts,
};

const content = `${JSON.stringify(manifest, null, 2)}\n`;
await writeFile(outputPath, content, "utf8");
await writeFile(fallbackOutputPath, content, "utf8");

console.log(
  JSON.stringify(
    {
      status: "ok",
      model_root: modelRoot,
      artifacts: artifacts.length,
      contract_sha256: artifactContractDigest,
      outputs: [outputPath, fallbackOutputPath],
    },
    null,
    2,
  ),
);
