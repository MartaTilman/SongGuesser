// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title SongGuesserAchievements
/// @notice Soulbound (non-transferable) ERC-1155 achievement badges for the
///         Song Guesser game. Tokens are minted by the backend submitter
///         wallet (the contract owner) directly to a player's address after
///         a game finishes. They can never be transferred, sold or
///         approved away -- they are a permanent, tamper-proof record that
///         a specific address actually earned that achievement.
contract SongGuesserAchievements is ERC1155, Ownable {
    // Achievement token IDs.
    uint256 public constant WINNER = 1;
    uint256 public constant PERFECT_ROUND = 2;
    uint256 public constant STREAK = 3;
    uint256 public constant FASTEST_ANSWER = 4;

    /// @dev Emitted once per (lobbyId, gameNumber) mint batch so an
    ///      indexer / frontend can look up which game an achievement batch
    ///      came from without decoding it off the ERC-1155 events alone.
    event AchievementsAwarded(
        address indexed player,
        string lobbyId,
        uint256 gameNumber,
        uint256[] ids,
        uint256[] amounts
    );

    constructor(string memory uri_, address initialOwner)
        ERC1155(uri_)
        Ownable(initialOwner)
    {}

    /// @notice Mint one or more achievement badges to a player after a
    ///         finished game. Only callable by the backend submitter wallet.
    function mintAchievements(
        address player,
        string calldata lobbyId,
        uint256 gameNumber,
        uint256[] calldata ids,
        uint256[] calldata amounts
    ) external onlyOwner {
        _mintBatch(player, ids, amounts, "");
        emit AchievementsAwarded(player, lobbyId, gameNumber, ids, amounts);
    }

    /// @notice Update the metadata URI (e.g. if it needs to move to a new host).
    function setURI(string calldata newUri) external onlyOwner {
        _setURI(newUri);
    }

    // ---- Soulbound: block every form of transfer ----
    //
    // OpenZeppelin v5 routes minting, burning AND transferring through the
    // single _update hook (from == address(0) is a mint, to == address(0)
    // is a burn, both non-zero is a transfer). We allow mints (and let the
    // owner burn a mis-issued badge), but reject any transfer between two
    // real addresses.
    function _update(address from, address to, uint256[] memory ids, uint256[] memory values)
        internal
        override
    {
        if (from != address(0) && to != address(0)) {
            revert("SongGuesserAchievements: soulbound, non-transferable");
        }
        super._update(from, to, ids, values);
    }

    function setApprovalForAll(address, bool) public pure override {
        revert("SongGuesserAchievements: soulbound, non-transferable");
    }
}
