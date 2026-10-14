const versions = {
  app: "1.0.0",
  node: "node-demo",
};

function getVersion(component) {
  return versions[component];
}

console.log(getVersion("app"));
console.log(getVersion("appp"));
