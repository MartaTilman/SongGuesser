// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SongGuesserAnchor {
    struct GameProof {
        string lobbyId;
        bytes32 chainHash;
        bytes32 merkleRoot;
        bytes32 leaderboardHash;
        uint256 blockCountBeforeFinal;
        address submitter;
        uint256 submittedAt;
    }

    mapping(bytes32 => GameProof) public proofs;

    event GameProofSubmitted(
        bytes32 indexed proofId,
        string lobbyId,
        bytes32 chainHash,
        bytes32 merkleRoot,
        bytes32 leaderboardHash,
        uint256 blockCountBeforeFinal,
        address indexed submitter
    );

    function submitGameProof(
        string calldata lobbyId,
        bytes32 chainHash,
        bytes32 merkleRoot,
        bytes32 leaderboardHash,
        uint256 blockCountBeforeFinal
    ) external returns (bytes32 proofId) {
        proofId = keccak256(
            abi.encodePacked(
                lobbyId,
                chainHash,
                merkleRoot,
                leaderboardHash,
                blockCountBeforeFinal
            )
        );

        require(proofs[proofId].submittedAt == 0, "Proof already submitted");

        proofs[proofId] = GameProof({
            lobbyId: lobbyId,
            chainHash: chainHash,
            merkleRoot: merkleRoot,
            leaderboardHash: leaderboardHash,
            blockCountBeforeFinal: blockCountBeforeFinal,
            submitter: msg.sender,
            submittedAt: block.timestamp
        });

        emit GameProofSubmitted(
            proofId,
            lobbyId,
            chainHash,
            merkleRoot,
            leaderboardHash,
            blockCountBeforeFinal,
            msg.sender
        );
    }
}
