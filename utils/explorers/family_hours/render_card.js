// Render the preview card a shared link shows (docs/images/family-hours-card.png)
// from the built page's own image, at the default family. It also writes
// family-hours-card.json: the figures on the card. tests/test_explorer_build.py
// fails when they no longer match the page's defaults, so re-run this after
// changing family_costs.json or the page's math.
//
//   python3 utils/explorers/family_hours/build.py --out /tmp/fam.html
//   PUP=$(npm root -g)/@mermaid-js/mermaid-cli/node_modules/puppeteer \
//     node utils/explorers/family_hours/render_card.js /tmp/fam.html docs/images
//
// Puppeteer is local tooling, as mmdc is for the diagrams.
const puppeteer = require(process.env.PUP || "puppeteer");
const fs = require("fs"), path = require("path");
(async () => {
  const [page, outDir] = process.argv.slice(2);
  const b = await puppeteer.launch({args: ["--no-sandbox"]});
  const p = await b.newPage();
  await p.goto("file://" + path.resolve(page));
  const r = await p.evaluate(async () => {
    if (encode(S) !== "") throw new Error("the page did not open at its defaults");
    const R = compute();
    return {png: (await makeImage()).toDataURL("image/png"),
            card: {total: hrs(R.total), w: S.w, cap: R.cap, status: status(R.total, R.cap, S.h)}};
  });
  fs.writeFileSync(path.join(outDir, "family-hours-card.png"), Buffer.from(r.png.split(",")[1], "base64"));
  fs.writeFileSync(path.join(outDir, "family-hours-card.json"), JSON.stringify(r.card, null, 2) + "\n");
  console.log("card:", JSON.stringify(r.card));
  await b.close();
})();
