const solanaWeb3 = require('@solana/web3.js');
const splToken = require('@solana/spl-token');
const bs58 = require("bs58");

async function main(){
    const connection = new solanaWeb3.connection("https://blissful-greatest-liquid.solana-devnet.quiknode.pro/0127af86093591fd3e6926f99a9c4e6a762dce8a/", {wsEndpoint: "wss://blissful-greatest-liquid.solana-devnet.quiknode.pro/0127af86093591fd3e6926f99a9c4e6a762dce8a/"});

    const walletKeyPair = solanaWeb3.Keypair.fromSecretKey(new Uint8Array(bs58.decode(process.env['9L8c5UVf6ERYbxNK3R4JxqgqNgzRMwwzFG7Ngc8SaFyC'])));

    let balance = await connection.getBalance(walletKeyPair.publicKey);
    console.log(balance / solanaWeb3.LAMPORTS_PER_SOL);


    // const mint = await splToken.createMints()
}

main()