import { directAbout, queryAbout, forwardedAbout } from "./about.mjs";
import {
  directDiagnostics,
  queryDiagnostics,
  forwardedDiagnostics,
} from "./diagnostics.mjs";

for (const [name, about, diagnostics] of [
  ["direct", directAbout, directDiagnostics],
  ["query", queryAbout, queryDiagnostics],
  ["forward", forwardedAbout, forwardedDiagnostics],
]) {
  console.log(name, JSON.stringify({
    about: about(),
    diagnostics: diagnostics(),
  }));
}
