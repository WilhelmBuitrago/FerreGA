import "@testing-library/jest-dom";

const baseUrl = "http://localhost";

globalThis.fetch = async (input: RequestInfo | URL) => {
  new URL(typeof input === "string" ? input : input.toString(), baseUrl);
  return new Response(JSON.stringify([]), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
