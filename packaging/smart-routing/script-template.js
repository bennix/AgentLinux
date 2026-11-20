// AgentLinux 智能分流
function main(config) {
  const direct = __DIRECT_RULES__;
  const match = (config.rules || []).find(rule => /^MATCH,/i.test(rule));
  const original = match && match.split(",")[1];
  const selectable = (config["proxy-groups"] || []).find(group => group.type === "select");
  const fallback = original && !["DIRECT", "REJECT", "PASS"].includes(original)
    ? original : (selectable && selectable.name) || ((config.proxies || [])[0] || {}).name;
  if (fallback) {
    config.rules = direct.concat(["MATCH," + fallback]);
    config["find-process-mode"] = "strict";
  }
  return config;
}
