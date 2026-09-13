// Real Ethereum wallet (MetaMask) connection. Separate from wallet.js,
// which is the internal RSA keypair used to sign in-game actions and
// still works on its own -- connecting MetaMask here is optional and only
// unlocks on-chain achievement badges (backend/blockchain/achievements.py
// mints to whatever address is verified here).

const SEPOLIA_CHAIN_ID_HEX = "0xaa36a7"; // 11155111 in hex

export function isMetaMaskAvailable() {
  return typeof window !== "undefined" && !!window.ethereum;
}

export function buildWalletLinkMessage(lobbyId, playerName, timestamp) {
  // Must match backend/blockchain/crypto_utils.py build_wallet_link_message
  // byte-for-byte, or signature verification on the backend will fail.
  return (
    "Song Guesser wallet link\n" +
    `Lobby: ${String(lobbyId || "").toUpperCase()}\n` +
    `Player: ${playerName}\n` +
    `Timestamp: ${timestamp}`
  );
}

async function ensureSepoliaNetwork() {
  const currentChainId = await window.ethereum.request({ method: "eth_chainId" });

  if (currentChainId === SEPOLIA_CHAIN_ID_HEX) {
    return;
  }

  try {
    await window.ethereum.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: SEPOLIA_CHAIN_ID_HEX }]
    });
  } catch (switchError) {
    // 4902 = chain isn't added to this MetaMask yet.
    if (switchError?.code === 4902) {
      await window.ethereum.request({
        method: "wallet_addEthereumChain",
        params: [
          {
            chainId: SEPOLIA_CHAIN_ID_HEX,
            chainName: "Sepolia",
            nativeCurrency: { name: "Sepolia ETH", symbol: "ETH", decimals: 18 },
            rpcUrls: ["https://rpc.sepolia.org"],
            blockExplorerUrls: ["https://sepolia.etherscan.io"]
          }
        ]
      });
    } else {
      throw switchError;
    }
  }
}

/**
 * Opens MetaMask, asks the player to connect an account, and makes sure
 * it's on Sepolia. Returns the connected address (does not sign anything
 * yet -- signing happens separately, once the lobby id is known, via
 * signWalletLink()).
 */
export async function connectEthWallet() {
  if (!isMetaMaskAvailable()) {
    throw new Error("MetaMask nije pronađen. Instaliraj MetaMask ekstenziju za Chrome.");
  }

  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  const address = accounts && accounts[0];

  if (!address) {
    throw new Error("Nijedan račun nije odabran u MetaMasku.");
  }

  await ensureSepoliaNetwork();

  return address;
}

/**
 * Signs a short proof-of-ownership message with the connected wallet so
 * the backend can verify this player really controls `address` before
 * ever minting an achievement to it.
 */
export async function signWalletLink(address, lobbyId, playerName) {
  const timestamp = Date.now();
  const message = buildWalletLinkMessage(lobbyId, playerName, timestamp);

  const signature = await window.ethereum.request({
    method: "personal_sign",
    params: [message, address]
  });

  return { address, signature, timestamp };
}
