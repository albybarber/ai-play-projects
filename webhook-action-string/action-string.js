const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function toActionString(str) {
  return str
    .trim()
    // split camelCase/PascalCase into separate words (e.g. "fileUploadCompleted" → "file Upload Completed")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    // replace any run of non-alphanumeric chars with a single dot
    .replace(/[^a-z0-9]+/g, ".")
    // trim leading/trailing dots
    .replace(/^\.+|\.+$/g, "");
}

const examples = [
  "File Created",
  "file upload completed",
  "Comment Uncompleted",
  "fileUploadCompleted",
  "🔥 Share Viewed! 🚀",
  "metadata value updated",
  "CUSTOM_FIELD_DELETED",
  "project--created",
  "A File has been deleted",
];

function prompt() {
  rl.question('\nEnter a string (or "q" to quit): ', (input) => {
    if (input.trim().toLowerCase() === "q") {
      rl.close();
      return;
    }
    console.log(`  → ${toActionString(input)}`);
    prompt();
  });
}

console.log("=== Webhook Action String Converter ===");
console.log("Pattern: resource.action (e.g. file.created, file.upload.completed)\n");
console.log("Examples:");
for (const ex of examples) {
  console.log(`  "${ex}" → ${toActionString(ex)}`);
}
prompt();
