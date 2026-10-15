import { createAsyncTaskList as original } from "./00-original.mjs";
import { createAsyncTaskList as renamed } from "./01-rename.mjs";
import { createAsyncTaskList as bridge } from "./02-map-bridge.mjs";
import { createAsyncTaskList as direct } from "./03-map-direct.mjs";

export const versions = [
  ["00-original", original],
  ["01-rename", renamed],
  ["02-map-bridge", bridge],
  ["03-map-direct", direct],
];
