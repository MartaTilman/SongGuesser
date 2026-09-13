# Prijedlog proširenja projekta "Song Guesser"

## Trenutno stanje projekta

Song Guesser je real-time multiplayer igra pogađanja pjesama (Vue 3 + FastAPI + WebSocketi). Projekt već sadrži blockchain komponentu koja igru čini provjerljivom i otpornom na namještanje rezultata:

- svaka partija u lobbyju vodi se kao vlastiti proof-of-work lanac blokova (svaki blok povezan hashem prethodnog, rudaren s zadanom težinom),
- prije svake pjesme generira se kriptografski "commitment" (hash + salt) koji dokazuje da pjesma nije naknadno promijenjena nakon što je runda već počela (commit-reveal shema),
- na kraju partije generira se finalni dokaz (chain hash, Merkle root, hash ljestvice) spreman za sidrenje na javni blockchain,
- pripremljen je Solidity ugovor (`SongGuesserAnchor.sol`) za to sidrenje na javni EVM testnet.

## Predloženo proširenje

Cilj proširenja je dovršiti i nadograditi blockchain sloj tako da rezultati igre i identitet igrača postanu stvarno, javno provjerljivi na Ethereum testnet mreži (Sepolia), umjesto da ostanu isključivo interna simulacija koncepta.

### 1. Integracija pravog Ethereum novčanika

Trenutno se identitet i potpisi igrača (pridruživanje lobbyju, slanje odgovora) temelje na internom RSA ključu koji preglednik sam generira i sprema lokalno. Proširenje bi to zamijenilo stvarnom integracijom MetaMask novčanika:

- igrač se spaja svojim Ethereum novčanikom prilikom ulaska u igru,
- akcije igrača (pridruživanje, slanje odgovora) potpisuju se njegovim stvarnim kriptografskim ključem (standardni `personal_sign` potpis),
- backend potpise provjerava kriptografskom verifikacijom potpisa nad javnom Ethereum adresom igrača.

Igra ostaje dostupna i bez spajanja novčanika (gost način), a spajanje novčanika otključava dodatne mogućnosti opisane u točki 2.

### 2. On-chain postignuća kao soulbound NFT-ovi

Nakon završetka partije, sustav bi na Sepolia testnet mreži izdavao neprenosive (soulbound) NFT tokene igračima koji su ostvarili određeno postignuće (pobjeda, savršena runda, niz točnih pogodaka, najbrži odgovor i sl.). Tehnički detalji:

- korišten je ERC-1155 standard, koji omogućuje više različitih tipova postignuća unutar jednog ugovora,
- tokeni su namjerno neprenosivi ("soulbound") — ne mogu se prodati ni prenijeti na drugu adresu, čime ostaju trajan i nepatvoriv dokaz da je igrač osobno ostvario dano postignuće,
- izdavanje tokena (mint) provodi backend automatski u ime igrača, pa igraču nije potreban vlastiti testni novac niti dodatna radnja — postignuće se jednostavno pojavi na njegovoj adresi.

Ovime se dosadašnji dokaz integriteta partije (koji je do sad ostajao samo zapisan lokalno) proširuje u stvarno, javno provjerljivo vlasništvo igrača na blockchainu.

### 3. Dodatni sadržajni modovi igre

Uz blockchain dio, planirano je i proširenje sadržaja igre kroz nove tematske modove biranja pjesama:

- mod isključivo s hrvatskim pjesmama,
- mod s "Yugoton" pjesmama (glazba s područja bivše Jugoslavije),
- mod s pjesmama Eurosonga.

Ovi modovi ne zadiru u blockchain arhitekturu, ali proširuju igrivost i prilagodljivost igre različitim skupinama igrača.

## Sažetak

Proširenje uključuje: (1) zamjenu internog kriptografskog ključa pravom integracijom Ethereum novčanika, (2) izdavanje neprenosivih NFT postignuća na javnom Ethereum testnetu (Sepolia) kao dokaz stvarno ostvarenih rezultata, te (3) nove sadržajne modove igre po žanru/regiji pjesama. Molim povratnu informaciju je li ovakav opseg proširenja dovoljan, ili je potrebno dodatno produbiti pojedini dio.
