# webhook-action-string

A Node.js script that converts any string into a webhook-style dot-notation action string.

## Usage

```sh
node action-string.js
```

Then type any string at the prompt and it will be converted:

```
"File Created"            → file.created
"file upload completed"   → file.upload.completed
"fileUploadCompleted"     → file.upload.completed
"🔥 Share Viewed! 🚀"    → share.viewed
"CUSTOM_FIELD_DELETED"    → custom.field.deleted
```

## How it works

1. Splits camelCase/PascalCase words
2. Lowercases everything
3. Replaces any run of non-alphanumeric characters with a single `.`
4. Trims leading/trailing dots
