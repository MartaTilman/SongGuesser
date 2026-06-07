const PRIVATE_KEY_STORAGE = "songGuesserPrivateKeyJwk";
const PUBLIC_KEY_STORAGE = "songGuesserPublicKeyJwk";

const algorithm = {
  name: "RSA-PSS",
  modulusLength: 2048,
  publicExponent: new Uint8Array([1, 0, 1]),
  hash: "SHA-256"
};

function base64UrlEncode(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";

  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });

  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

export function canonicalJson(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }

  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(",")}}`;
  }

  return JSON.stringify(value);
}

async function importPrivateKey(jwk) {
  return crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSA-PSS", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

export async function ensureWallet() {
  const savedPublicKey = localStorage.getItem(PUBLIC_KEY_STORAGE);
  const savedPrivateKey = localStorage.getItem(PRIVATE_KEY_STORAGE);

  if (savedPublicKey && savedPrivateKey) {
    return {
      publicKey: JSON.parse(savedPublicKey),
      privateKey: await importPrivateKey(JSON.parse(savedPrivateKey))
    };
  }

  const keyPair = await crypto.subtle.generateKey(
    algorithm,
    true,
    ["sign", "verify"]
  );
  const publicKeyJwk = await crypto.subtle.exportKey("jwk", keyPair.publicKey);
  const privateKeyJwk = await crypto.subtle.exportKey("jwk", keyPair.privateKey);

  publicKeyJwk.alg = "PS256";
  publicKeyJwk.key_ops = ["verify"];
  privateKeyJwk.alg = "PS256";
  privateKeyJwk.key_ops = ["sign"];

  localStorage.setItem(PUBLIC_KEY_STORAGE, JSON.stringify(publicKeyJwk));
  localStorage.setItem(PRIVATE_KEY_STORAGE, JSON.stringify(privateKeyJwk));

  return {
    publicKey: publicKeyJwk,
    privateKey: await importPrivateKey(privateKeyJwk)
  };
}

export function buildSignedAction(action, lobbyId, playerName, payload = {}) {
  return {
    action,
    lobby_id: String(lobbyId || "").toUpperCase(),
    player: playerName,
    payload
  };
}

export async function signPayload(privateKey, payload) {
  const encoded = new TextEncoder().encode(canonicalJson(payload));
  const signature = await crypto.subtle.sign(
    {
      name: "RSA-PSS",
      saltLength: 32
    },
    privateKey,
    encoded
  );

  return {
    payload,
    signature: base64UrlEncode(signature)
  };
}
