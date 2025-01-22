import fetch from "node-fetch";

import aws4 from "aws4";

const apiGatewayUrl =
  "https://xxxx.execute-api.ap-northeast-1.amazonaws.com/prod" +
  "/scenes";

const url = new URL(apiGatewayUrl);
const apiKey = "xxxxx";
const opts = {
  method: "GET",
  host: url.hostname,
  path: url.pathname,
  service: "execute-api",
  region: "ap-northeast-1",
  headers: {
    "x-api-key": apiKey,
  },
};

aws4.sign(opts);

console.log(opts);
const response = await fetch(apiGatewayUrl, {
  headers: opts.headers,
});

console.log(await response.json());
