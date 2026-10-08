const API = "http://localhost:8000";

function errorText(data) {
  if (!data) return "";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map(d => d.msg).join(", ");
  return "";
}

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(API + path, {
      method: options.method || "GET",
      credentials: "include",                       // sends the login cookie
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch (e) {
    throw new Error("Cannot reach the server. Is the backend running?");
  }
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) {
    const err = new Error(errorText(data) || "Something went wrong");
    err.status = res.status;
    throw err;
  }
  return data;
}