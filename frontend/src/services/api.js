const API = "http://127.0.0.1:8000"

export async function createLobby(player) {

    const res = await fetch(`${API}/create_lobby`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            player_name: player
        })
    })

    return res.json()
}