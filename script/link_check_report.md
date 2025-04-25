# 文档链接检查报告

生成时间：2025-04-23 07:13:12

## 1. 图片链接问题

### 1.1 缺失图片文件
以下图片文件未找到，需要确保它们存在于 `/treasurenet-docs/static/img/docs` 目录下：

## 2. 外部链接问题

### 2.1 超时链接
以下外部链接访问超时，需要验证其可访问性：

#### TCash/qa.md
- `https://124.70.23.119:3021/en/docs/TCash/financial-operations/`

#### about/introduction.md
> 这两个链接，点进去之后的链接无效
- `https://discord.com/invite/treasurenet`
- `https://t.me/Treasurenet_io`

#### developers/faq.md
- `https://google.com`
> 哈哈，这是测试链的水龙头链接，让用户自己 Google 去吗。

#### developers/guides/wallet-integration.md
- `https://docs.metamask.io/guide/`
> 能打开
> 点进去后，会重定向，实际的链接是：https://docs.metamask.io/wallet/

#### fundamentals/transfer-tokens.md
- `https://124.70.23.119:3021/docs/fundamentals/wallets/coinbase`
- `https://124.70.23.119:3021/docs/fundamentals/wallets/metamask`

#### governance/overview.md
- `https://discord.gg/treasurenet`
- `https://t.me/+hN6G5mGAlD8xMmI5`
> 上面两个链接，点进去后的链接无效

#### validators/join-mainnet.md
- `https://google.com`
> Aha

### 2.2 格式错误的链接
以下链接格式不正确，需要补充完整的URL：

#### api/officialContracts/TCash.md
- `http://`

#### api/officialContracts/bid.md
- `http://`

#### api/officialContracts/tat.md
- `http://`

#### developers/clients.md
- `https://`

#### developers/localnet/single-node.md
- `https://`

#### validators/join-testnet.md
- `https://`

### 2.3 空链接
以下链接为空或只包含锚点，需要补充实际链接：

#### validators/setup/run-a-validator.md
- `#unjail-validator`

#### fundamentals/cross-chain.md
- `https://services.testnet.treasurenet.io/transfer`
> 404

#### assets/tat_mint/production_data_uploader.md
- `https://github.com/treasurenetprotocol/treasurenet-tnservices-productiondata-uploader`
> 404

#### protocolDevelopers/concepts/gas-and-fees.md
- `https://docs.cosmos.network/main/basics/gas-fees.html`
> Page Not Found

#### validators/faq.md
- `https://docs.tendermint.com/main/introduction/what-is-tendermint.html`
> 404

#### validators/join-mainnet.md
- `https://github.com/treasurenetprotocol/addrbook.json`
> 404

## 3. 建议添加的链接

### api/eth-json-rpc/eth-methods.md
- Ethereum Contract ABI
 - Documentation for Ethereum Contract ABI

  上下文：code of a contract OR the hash of the invoked method signature and encoded parameters. For details see Ethereum Contract ABI
- nonce: QUANTITY - (optional) Integer of a nonce. This allows to overwrit
- Ethereum Contract ABI in the Solidity documentation
 - Documentation for Ethereum Contract ABI in the Solidity documentation

  上下文：nsaction
- data: DATA - (optional) Hash of the method signature and encoded parameters. For details see Ethereum Contract ABI in the Solidity documentation
- Block number or Block Hash ([EIP-1898](htt

### validators/quickStart/installation.md
- 1.18 - Version history
  上下文：sure you have set up the go environment and git.

   :::caution
   ❗️ Treasurenet build requires Go version 1.18+ Golang website download: https://golang.org/dl/
   :::

2. Open the official download

### validators/setup/configuration.md
- DBBackend - Documentation for DBBackend
  上下文：) "kv" (default) - the simplest possible indexer, backed by key-value storage (defaults to levelDB; see DBBackend).
# 		- When "kv" is chosen "tx.height" and "tx.hash" will always be indexed.
indexer

## 4. 统计信息

- 检查的文件总数：124
- 发现的问题：
  - 缺失图片：0个
  - 超时链接：13个
  - 格式错误链接：11个
  - 空链接：1个
  - 建议添加链接：4个
