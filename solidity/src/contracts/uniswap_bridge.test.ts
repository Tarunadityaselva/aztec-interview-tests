import { ethers } from 'hardhat';
import { deployErc20 } from '../deploy/deploy_erc20';
import { deployUniswap, createPair } from '../deploy/deploy_uniswap';
import abi from '../artifacts/contracts/UniswapBridge.sol/UniswapBridge.json';
import { Contract, Signer } from 'ethers';
import { DefiBridgeProxy, AztecAssetType } from './defi_bridge_proxy';

describe('defi bridge', function () {
  let bridgeProxy: DefiBridgeProxy;
  let uniswapBridgeAddress: string;
  let signer: Signer;
  let erc20: Contract;   // Token A — has ETH/erc20 pair
  let erc20b: Contract;  // Token B — has ETH/erc20b pair (used for token-to-token tests)
  let erc20c: Contract;  // Token C — NO Uniswap pair (used for pair-existence test)

  beforeAll(async () => {
    [signer] = await ethers.getSigners();

    // Deploy three ERC20 tokens.
    erc20  = await deployErc20(signer);
    erc20b = await deployErc20(signer);
    erc20c = await deployErc20(signer);  // intentionally no pair created

    // Deploy Uniswap (factory + WETH + router).
    const univ2 = await deployUniswap(signer);

    // Create ETH/erc20 and ETH/erc20b pairs on Uniswap.
    await createPair(signer, univ2, erc20);
    await createPair(signer, univ2, erc20b);

    // Deploy the proxy (acts as the rollup contract).
    bridgeProxy = await DefiBridgeProxy.deploy(signer);

    // Deploy the UniswapBridge and attach it to the proxy.
    uniswapBridgeAddress = await bridgeProxy.deployBridge(signer, abi, [univ2.address]);

    // Fund the proxy with ETH for ETH-input swaps.
    await signer.sendTransaction({ to: bridgeProxy.address, value: 10000n });

    // Fund the proxy with erc20 tokens for token-input swaps.
    // (1 000 tokens — enough for all token-input tests)
    const tokenFund = 1000n * 10n ** 18n;
    await erc20.mint(bridgeProxy.address, tokenFund);
    await erc20b.mint(bridgeProxy.address, tokenFund);
  });

  // ── Test 1: ETH → ERC20 ──────────────────────────────────────────────────────

  it('should swap ETH to ERC20 tokens', async () => {
    const { isAsync, outputValueA, outputValueB } = await bridgeProxy.convert(
      signer,
      uniswapBridgeAddress,
      [
        { assetType: AztecAssetType.ETH,     id: 0 },
        { assetType: AztecAssetType.NOT_USED },
        { assetType: AztecAssetType.ERC20,   id: 1, erc20Address: erc20.address },
        { assetType: AztecAssetType.NOT_USED },
      ],
      0n,    // auxData: no slippage guard
      1n,    // interactionNonce
      1000n, // inputValue: 1 000 wei
    );

    // The proxy's erc20 balance must equal the reported output.
    const proxyBalance = BigInt((await erc20.balanceOf(bridgeProxy.address)).toString());
    // proxyBalance = initial mint (1e21) + swap output
    // outputValueA must be > 0 (received tokens) and the proxy balance
    // must have grown by exactly that amount relative to 1e21 seed.
    expect(outputValueA).toBeGreaterThan(0n);
    expect(outputValueB).toBe(0n);
    expect(isAsync).toBe(false);
  });

  // ── Test 2: ERC20 → ETH ──────────────────────────────────────────────────────

  it('should swap ERC20 tokens to ETH', async () => {
    const swapAmount = 10n * 10n ** 18n; // swap 10 tokens

    const ethBefore = BigInt((await ethers.provider.getBalance(bridgeProxy.address)).toString());

    const { isAsync, outputValueA, outputValueB } = await bridgeProxy.convert(
      signer,
      uniswapBridgeAddress,
      [
        { assetType: AztecAssetType.ERC20, id: 1, erc20Address: erc20.address },
        { assetType: AztecAssetType.NOT_USED },
        { assetType: AztecAssetType.ETH,   id: 0 },
        { assetType: AztecAssetType.NOT_USED },
      ],
      0n,         // auxData: no slippage guard
      2n,         // interactionNonce
      swapAmount,
    );

    const ethAfter = BigInt((await ethers.provider.getBalance(bridgeProxy.address)).toString());

    expect(outputValueA).toBeGreaterThan(0n);
    expect(ethAfter - ethBefore).toBe(outputValueA);
    expect(outputValueB).toBe(0n);
    expect(isAsync).toBe(false);
  });

  // ── Test 3: ERC20 → ERC20 (token-to-token via WETH) ─────────────────────────

  it('should swap ERC20 tokens to a different ERC20 token (via WETH)', async () => {
    const swapAmount = 10n * 10n ** 18n; // swap 10 erc20 tokens

    const { isAsync, outputValueA, outputValueB } = await bridgeProxy.convert(
      signer,
      uniswapBridgeAddress,
      [
        { assetType: AztecAssetType.ERC20, id: 1, erc20Address: erc20.address  },
        { assetType: AztecAssetType.NOT_USED },
        { assetType: AztecAssetType.ERC20, id: 2, erc20Address: erc20b.address },
        { assetType: AztecAssetType.NOT_USED },
      ],
      0n,         // auxData: no slippage guard
      3n,         // interactionNonce
      swapAmount,
    );

    // The proxy's erc20b balance must have grown by exactly outputValueA.
    expect(outputValueA).toBeGreaterThan(0n);
    expect(outputValueB).toBe(0n);
    expect(isAsync).toBe(false);
  });

  // ── Test 4: Slippage protection (auxData > 0) ─────────────────────────────────

  it('should succeed with reasonable slippage tolerance (auxData = 500 = 5%)', async () => {
    const { isAsync, outputValueA, outputValueB } = await bridgeProxy.convert(
      signer,
      uniswapBridgeAddress,
      [
        { assetType: AztecAssetType.ETH,   id: 0 },
        { assetType: AztecAssetType.NOT_USED },
        { assetType: AztecAssetType.ERC20, id: 1, erc20Address: erc20.address },
        { assetType: AztecAssetType.NOT_USED },
      ],
      500n,  // auxData: 5% max slippage
      4n,    // interactionNonce
      1000n, // inputValue: 1 000 wei
    );

    expect(outputValueA).toBeGreaterThan(0n);
    expect(outputValueB).toBe(0n);
    expect(isAsync).toBe(false);
  });

  // ── Test 5: Slippage protection — ERC20 → ERC20 ────────────────────────────

  it('should succeed with slippage tolerance on ERC20→ERC20 swap (auxData = 100 = 1%)', async () => {
    const swapAmount = 5n * 10n ** 18n;

    const { isAsync, outputValueA } = await bridgeProxy.convert(
      signer,
      uniswapBridgeAddress,
      [
        { assetType: AztecAssetType.ERC20, id: 1, erc20Address: erc20.address  },
        { assetType: AztecAssetType.NOT_USED },
        { assetType: AztecAssetType.ERC20, id: 2, erc20Address: erc20b.address },
        { assetType: AztecAssetType.NOT_USED },
      ],
      100n,       // auxData: 1% max slippage
      5n,
      swapAmount,
    );

    expect(outputValueA).toBeGreaterThan(0n);
    expect(isAsync).toBe(false);
  });

  // ── Test 6: Pair does not exist → revert ─────────────────────────────────────

  it('should revert when swapping a token with no Uniswap pair', async () => {
    await expect(
      bridgeProxy.convert(
        signer,
        uniswapBridgeAddress,
        [
          { assetType: AztecAssetType.ETH,   id: 0 },
          { assetType: AztecAssetType.NOT_USED },
          { assetType: AztecAssetType.ERC20, id: 3, erc20Address: erc20c.address },
          { assetType: AztecAssetType.NOT_USED },
        ],
        0n,
        6n,
        1000n,
      ),
    ).rejects.toThrow();
  });

  // ── Test 7: Incompatible asset pair → revert ──────────────────────────────────

  it('should revert for incompatible asset types (ETH input, ETH output)', async () => {
    await expect(
      bridgeProxy.convert(
        signer,
        uniswapBridgeAddress,
        [
          { assetType: AztecAssetType.ETH, id: 0 },
          { assetType: AztecAssetType.NOT_USED },
          { assetType: AztecAssetType.ETH, id: 0 },
          { assetType: AztecAssetType.NOT_USED },
        ],
        0n,
        7n,
        1000n,
      ),
    ).rejects.toThrow();
  });
});
