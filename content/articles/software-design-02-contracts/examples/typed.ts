const versions = {
  app: "1.0.0",
  node: "node-demo",
};

export function getVersion(component: "app" | "node"): string {
  if (component !== "app" && component !== "node") {
    throw new Error("只支持 app 或 node");
  }

  return versions[component];
}
